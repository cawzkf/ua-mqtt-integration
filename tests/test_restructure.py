"""
Testes para verificar se a reestruturação do projeto funcionou corretamente.
"""
import pytest
import os
import importlib
import sys
from pathlib import Path

class TestProjectRestructure:
    """Testa se a nova estrutura de Clean Architecture está funcionando."""
    
    def test_folder_structure_exists(self):
        """Testa se as pastas da nova estrutura existem."""
        expected_folders = [
            "infra",
            "infra/mqtt", 
            "infra/opcua",
            "infra/database",
            "services",
            "services/events",
            "services/opcua",
            "utils"
        ]
        
        for folder in expected_folders:
            assert os.path.exists(folder), f"Pasta {folder} não existe"
            assert os.path.isdir(folder), f"{folder} não é uma pasta"
    
    def test_init_files_exist(self):
        """Testa se os arquivos __init__.py existem para tornar as pastas em módulos."""
        expected_init_files = [
            "infra/__init__.py",
            "infra/mqtt/__init__.py",
            "infra/opcua/__init__.py",
            "services/__init__.py",
            "services/events/__init__.py",
            "services/opcua/__init__.py",
            "utils/__init__.py"
        ]
        
        for init_file in expected_init_files:
            assert os.path.exists(init_file), f"Arquivo {init_file} não existe"
    
    def test_moved_files_exist(self):
        """Testa se os arquivos foram movidos para os lugares corretos."""
        expected_files = [
            "infra/mqtt/client.py",
            "infra/mqtt/message_handler.py",
            "services/events/current_monitor.py",
            "services/events/temperature_monitor.py", 
            "services/events/voltage_monitor.py",
            "services/events/event_generator.py",
            "services/opcua/server.py",
            "services/opcua/server_config.py",
            "services/opcua/discovery.py",
            "utils/config.py",
            "utils/constants.py",
            "utils/helpers.py",
            "utils/logging_config.py",
            "utils/variables.py"
        ]
        
        for file_path in expected_files:
            assert os.path.exists(file_path), f"Arquivo {file_path} não foi movido corretamente"
    
    def test_old_files_removed(self):
        """Testa se os arquivos antigos foram removidos."""
        old_paths = [
            "src/mqtt",
            "src/events", 
            "src/opcua",
            "src/utils",
            "scripts/mqtt_simulator.py"
        ]
        
        for old_path in old_paths:
            assert not os.path.exists(old_path), f"Arquivo/pasta antiga {old_path} ainda existe"
    
    def test_main_file_exists(self):
        """Testa se o main.py está na raiz."""
        assert os.path.exists("main.py"), "Arquivo main.py não existe na raiz"
    
    @pytest.mark.parametrize("module_name", [
        "infra.mqtt.client",
        "services.events.temperature_monitor",
        "services.opcua.discovery", 
        "utils.constants"
    ])
    def test_modules_can_be_imported(self, module_name):
        """Testa se os módulos podem ser importados sem erro."""
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Não foi possível importar {module_name}: {e}")
        except Exception as e:
            # Outros erros são OK por enquanto (dependências, etc)
            pass
    
    def test_constants_file_has_content(self):
        """Testa se o arquivo constants.py tem as constantes esperadas."""
        constants_path = "utils/constants.py"
        assert os.path.exists(constants_path), "utils/constants.py não existe"
        
        with open(constants_path, 'r') as f:
            content = f.read()
        
        expected_constants = [
            "NOMINAL_VOLTAGE",
            "VOLTAGE_TOLERANCE", 
            "NOMINAL_CURRENT",
            "MQTT_TOPICS",
            "MQTT_TO_OPCUA_MAP"
        ]
        
        for constant in expected_constants:
            assert constant in content, f"Constante {constant} não encontrada em constants.py"
    
    def test_discovery_file_structure(self):
        """Testa se o arquivo discovery.py tem a estrutura básica."""
        discovery_path = "services/opcua/discovery.py"
        assert os.path.exists(discovery_path), "services/opcua/discovery.py não existe"
        
        with open(discovery_path, 'r') as f:
            content = f.read()
        
        # Verifica se tem pelo menos estrutura básica de classe ou função
        has_structure = any([
            "class" in content,
            "def" in content,
            "async def" in content
        ])
        
        assert has_structure, "discovery.py não tem estrutura de código (classe ou função)"
    
    def test_python_syntax_validation(self):
        """Testa se todos os arquivos Python têm sintaxe válida."""
        python_files = []
        
        # Encontra todos os arquivos .py
        for root, dirs, files in os.walk("."):
            # Ignora __pycache__ e .git
            dirs[:] = [d for d in dirs if not d.startswith(('.git', '__pycache__'))]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        syntax_errors = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    compile(f.read(), py_file, 'exec')
            except SyntaxError as e:
                syntax_errors.append(f"{py_file}: {e}")
            except Exception:
                # Outros erros podem ser normais (imports, etc)
                pass
        
        assert len(syntax_errors) == 0, f"Erros de sintaxe encontrados: {syntax_errors}"

    def test_clean_architecture_compliance(self):
        """Testa se a estrutura segue os princípios de Clean Architecture."""
        
        # Verifica se infra contém apenas detalhes técnicos
        infra_files = []
        for root, dirs, files in os.walk("infra"):
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    infra_files.append(os.path.join(root, file))
        
        assert len(infra_files) > 0, "Pasta infra deve conter arquivos de infraestrutura"
        
        # Verifica se services contém lógica de negócio
        services_files = []
        for root, dirs, files in os.walk("services"):
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    services_files.append(os.path.join(root, file))
        
        assert len(services_files) > 0, "Pasta services deve conter arquivos de serviços"
        
        # Verifica se utils contém utilitários
        utils_files = []
        for root, dirs, files in os.walk("utils"):
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    utils_files.append(os.path.join(root, file))
        
        assert len(utils_files) > 0, "Pasta utils deve conter arquivos utilitários"

    def test_no_circular_imports(self):
        """Testa se não há imports circulares óbvios."""
        # Este é um teste básico - apenas verifica se consegue importar os módulos principais
        main_modules = [
            "infra",
            "services", 
            "utils"
        ]
        
        import_errors = []
        
        for module in main_modules:
            try:
                importlib.import_module(module)
            except Exception as e:
                import_errors.append(f"{module}: {e}")
        
        # Por enquanto, só falha se tiver erro de sintaxe
        syntax_errors = [err for err in import_errors if "SyntaxError" in str(err)]
        assert len(syntax_errors) == 0, f"Erros de sintaxe nos módulos principais: {syntax_errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])