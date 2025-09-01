import uuid
import traceback
from datetime import datetime, timezone
from asyncua import ua


async def generate_event_properly(event_generator, event_type, message, severity, **extra_props):
    try:
        event_generator.event.EventId = ua.Variant(uuid.uuid4().bytes, ua.VariantType.ByteString)
        event_generator.event.Time = ua.Variant(datetime.now(timezone.utc), ua.VariantType.DateTime)
        event_generator.event.ReceiveTime = ua.Variant(datetime.now(timezone.utc), ua.VariantType.DateTime)
        event_generator.event.Message = ua.Variant(ua.LocalizedText(message or ""), ua.VariantType.LocalizedText)
        event_generator.event.Severity = ua.Variant(severity, ua.VariantType.UInt16)

        for name, val in extra_props.items():
            if hasattr(event_generator.event, name):
                if isinstance(val, str):
                    v = ua.Variant(val, ua.VariantType.String)
                elif isinstance(val, bool):
                    v = ua.Variant(val, ua.VariantType.Boolean)
                elif isinstance(val, int):
                    v = ua.Variant(val, ua.VariantType.Int32)
                elif isinstance(val, float):
                    v = ua.Variant(val, ua.VariantType.Float)
                else:
                    v = ua.Variant(str(val), ua.VariantType.String)
                setattr(event_generator.event, name, v)

        await event_generator.trigger()
        
    except Exception as e:
        print(f"Erro ao gerar evento: {e}")
        traceback.print_exc()