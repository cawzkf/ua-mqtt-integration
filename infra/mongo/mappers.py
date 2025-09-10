import uuid
import logging
from datetime import datetime, timezone
import asyncua.ua as ua
from services.events.event_generator import generate_event_properly
from asyncua.ua import Variant, VariantType, LocalizedText, NodeId
from asyncua.common.events import Event

logger = logging.getLogger(__name__)
logging.basicConfig(
    level = logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)

def nodeid_to_bson(nid: ua.NodeId) -> dict:
    return {"ns": nid.NamespaceIndex, "id": nid.Identifier, "t": int(nid.NodeIdType)}

def nodeid_from_bson(d: dict) -> ua.NodeId:
    return ua.NodeId(d["id"], d["ns"], ua.NodeIdType(d["t"]))

def datavalue_to_dict(dv: ua.DataValue) -> dict:
    now = datetime.now(timezone.utc)
    src_ts = dv.SourceTimestamp if isinstance(dv.SourceTimestamp, datetime) else now
    srv_ts = dv.ServerTimestamp if isinstance(dv.ServerTimestamp, datetime) else now
    if src_ts.tzinfo is None:
        src_ts = src_ts.replace(tzinfo=timezone.utc)
    if srv_ts.tzinfo is None:
        srv_ts = srv_ts.replace(tzinfo=timezone.utc)

    return {
        "variant": dv.Value.VariantType.value if dv.Value else VariantType.Null.value,
        "timestamp": src_ts,
        "server_timestamp": srv_ts,
        "value": dv.Value.Value if dv.Value else None,
    }

def datavalue_from_dict(data: dict) -> ua.DataValue:
    try:
        variant = Variant(
            Value=data.get("value", 0.0),
            VariantType=VariantType(data.get("variant", VariantType.Double.value)),
        )

        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if not isinstance(ts, datetime):
            ts = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        sts = data.get("server_timestamp")
        if isinstance(sts, str):
            sts = datetime.fromisoformat(sts.replace("Z", "+00:00"))
        if not isinstance(sts, datetime):
            sts = datetime.now(timezone.utc)
        if sts.tzinfo is None:
            sts = sts.replace(tzinfo=timezone.utc)

        return ua.DataValue(variant, SourceTimestamp=ts, ServerTimestamp=sts)
    except Exception:
        now = datetime.now(timezone.utc)
        return ua.DataValue(Variant(0.0, VariantType.Double), SourceTimestamp=now, ServerTimestamp=now)


def _vt_to_int(vt) -> int:
    if hasattr(vt, 'value'):
        return int(vt.value)
    return int(vt)

def event_to_dict(event: generate_event_properly) -> dict:
    out = {}

    try:
        v = getattr(event, "EventId", None)
        val = getattr(v, "Value", None)
        out["EventId"] = {"VariantType": _vt_to_int(ua.VariantType.ByteString),
                          "Value": val if val is not None else uuid.uuid4().bytes}
    except Exception:
        out["EventId"] = {"VariantType": _vt_to_int(ua.VariantType.ByteString),
                          "Value": uuid.uuid4().bytes}

    try:
        v = getattr(event, "EventType", None)
        nid = getattr(v, "Value", None)
        if nid is not None:
            out["EventType"] = {"VariantType": _vt_to_int(ua.VariantType.NodeId),
                                "Value": nodeid_to_bson(nid)}
    except Exception:
        pass
    
    try:
        v = getattr(event, "SourceNode", None)
        nid = getattr(v, "Value", None)
        if nid is not None:
            out["SourceNode"] = {"VariantType": _vt_to_int(ua.VariantType.NodeId),
                                 "Value": nodeid_to_bson(nid)}
    except Exception:
        pass
    
    try:
        v = getattr(event, "SourceName", None)
        val = getattr(v, "Value", None)
        if val is not None:
            out["SourceName"] = {"VariantType": _vt_to_int(ua.VariantType.String), "Value": val}
    except Exception:
        pass

    for field in ("Time", "ReceiveTime"):
        try:
            v = getattr(event, field, None)
            val = getattr(v, "Value", None)
            if not isinstance(val, datetime):
                val = datetime.now(timezone.utc)
            out[field] = {"VariantType": _vt_to_int(ua.VariantType.DateTime), "Value": val}
        except Exception:
            out[field] = {"VariantType": _vt_to_int(ua.VariantType.DateTime),
                          "Value": datetime.now(timezone.utc)}

    try:
        v = getattr(event, "Message", None)
        txt = ""
        if v is not None:
            lv = getattr(v, "Value", None)
            txt = getattr(lv, "Text", None) or str(lv) or ""
        out["Message"] = {"VariantType": _vt_to_int(ua.VariantType.LocalizedText), "Value": txt}
    except Exception:
        out["Message"] = {"VariantType": _vt_to_int(ua.VariantType.LocalizedText), "Value": txt}

    try:
        v = getattr(event, "Severity", None)
        val = getattr(v, "Value", None)
        
        logger.info("=== SEVERITY PROCESSING ===")
        logger.info("Severity object: %s", v)
        logger.info("Severity value: %s", val)
        
        if val is None:
            if hasattr(event, 'Severity') and not hasattr(event.Severity, 'Value'):
                val = event.Severity
                logger.info("Using direct severity: %s", val)
            else:
                for attr_name in dir(event):
                    if 'severity' in attr_name.lower():
                        attr_val = getattr(event, attr_name, None)
                        logger.info("Found severity-like attr %s: %s", attr_name, attr_val)
                        if attr_val is not None:
                            if hasattr(attr_val, 'Value'):
                                val = attr_val.Value
                            else:
                                val = attr_val
                            break

        logger.info("Final severity value: %s", val)
        logger.info("=== END SEVERITY PROCESSING ===")
        
        out["Severity"] = {"VariantType": _vt_to_int(ua.VariantType.UInt16), "Value": val}
    except Exception as e:
        logger.warning("Error processing severity: %s", e)

    # MELHORAR a captura de campos personalizados
    logger.info("=== PROCESSING CUSTOM FIELDS ===")
    
    # Lista de campos personalizados esperados
    custom_fields = ['CaseTemperature', 'VoltagePhase', 'CurrentPhase']
    
    # Primeiro, tentar campos personalizados conhecidos
    for field_name in custom_fields:
        try:
            if hasattr(event, field_name):
                attr = getattr(event, field_name)
                logger.info("Found custom field %s: %s", field_name, attr)
                
                if hasattr(attr, 'Value') and hasattr(attr, 'VariantType'):
                    val = getattr(attr, "Value", None)
                    vt = getattr(attr, "VariantType", None)
                    
                    if val is not None:
                        out[field_name] = {
                            "VariantType": _vt_to_int(vt) if vt else _vt_to_int(ua.VariantType.String),
                            "Value": val
                        }
                        logger.info("Added custom field %s with value %s", field_name, val)
                elif attr is not None:
                    # Se não é um Variant, trata como valor direto
                    out[field_name] = {
                        "VariantType": _vt_to_int(ua.VariantType.String),
                        "Value": str(attr)
                    }
                    logger.info("Added direct custom field %s with value %s", field_name, attr)
        except Exception as e:
            logger.warning("Error processing custom field %s: %s", field_name, e)
    
    # Depois, varrer todos os outros atributos (como estava fazendo antes)
    for attr_name in dir(event):
        if (attr_name.startswith('_') or 
            attr_name in ['EventId', 'Time', 'ReceiveTime', 'Message', 'Severity', 
                         'EventType', 'SourceNode', 'SourceName'] + custom_fields):
            continue
            
        try:
            attr = getattr(event, attr_name)
            logger.info("Checking additional attr: %s = %s", attr_name, attr)
            
            if hasattr(attr, 'Value') and hasattr(attr, 'VariantType'):
                val = getattr(attr, "Value", None)
                vt = getattr(attr, "VariantType", None)
                
                if val is not None:
                    out[attr_name] = {
                        "VariantType": _vt_to_int(vt) if vt else _vt_to_int(ua.VariantType.String),
                        "Value": val
                    }
                    logger.info("Added additional field %s with value %s", attr_name, val)
        except Exception as e:
            logger.warning("Error processing additional attr %s: %s", attr_name, e)
    
    logger.info("=== END PROCESSING CUSTOM FIELDS ===")
    logger.info("Final event dict keys: %s", list(out.keys()))

    return out

def event_from_dict(data: dict) -> Event:
    ev = Event()

    def _vt(v):
        return ua.VariantType(v) if isinstance(v, int) else ua.VariantType(int(v))

    for k, meta in data.items():
        if k == "_id":
            continue

        vt  = meta.get("VariantType") if isinstance(meta, dict) else None
        val = meta.get("Value")       if isinstance(meta, dict) else None

        if k == "Message":
            lt = LocalizedText(Text=(val or ""))
            ev.add_property(k, Variant(lt, ua.VariantType.LocalizedText), None)

        elif k in ("EventType", "SourceNode"):
            if isinstance(val, dict):
                nid = NodeId(val.get("id"), val.get("ns"), ua.NodeIdType(val.get("t")))
                ev.add_property(k, Variant(nid, ua.VariantType.NodeId), None)

        elif k in ("Time", "ReceiveTime"):
            if not isinstance(val, datetime):
                try:
                    val = datetime.fromisoformat(val)
                except Exception:
                    val = datetime.now(timezone.utc)
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            ev.add_property(k, Variant(val, ua.VariantType.DateTime), None)

        elif k == "EventId":
            if isinstance(val, str):
                try:
                    val = bytes.fromhex(val)
                except Exception:
                    val = uuid.uuid4().bytes
            ev.add_property(k, Variant(val, ua.VariantType.ByteString), None)

        elif k == "Severity":
            try:
                sval = 100 if val is None else int(val)
            except Exception:
                sval = 100
            ev.add_property(k, Variant(sval, ua.VariantType.UInt16), None)

        else:
            try:
                ev.add_property(k, Variant(val, _vt(vt)), None)
            except Exception:
                ev.add_property(k, Variant(str(val), ua.VariantType.String), None)

    return ev
