class Registers:
    def __init__(self):
        self.INPUT_REGISTERS   = [0] * 20
        self.HOLDING_REGISTERS = [0] * 30
        
    def read_hr(self, order):
        return self.HOLDING_REGISTERS[order]
        
    def read_ir(self, order):
        return self.INPUT_REGISTERS[order]
    
    def write_hr(self, order, data):
        self.HOLDING_REGISTERS[order] = data
        
    def write_ir(self, order, data):
        self.INPUT_REGISTERS[order] = data
        
    def length_hr(self):
        return len(self.HOLDING_REGISTERS)
    
    def length_ir(self):
        return len(self.INPUT_REGISTERS)
    
        
REGS = Registers()