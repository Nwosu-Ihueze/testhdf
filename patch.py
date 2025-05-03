import sys
import types

# Create an empty mock module
class MockModule(types.ModuleType):
    def __init__(self, name):
        super().__init__(name)
    
    def __getattr__(self, name):
        return None

# Create and insert mock modules
sys.modules['chromadb'] = MockModule('chromadb')
sys.modules['karo.memory.services.chromadb_service'] = MockModule('karo.memory.services.chromadb_service')