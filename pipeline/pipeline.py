# pipeline.py

"""
Simulación del pipeline básico: IF → ID → EX
Responsabilidad:
 - Coordinar el flujo entre etapas.
 - Ejecutar instrucciones paso a paso.
 - Recolectar métricas globales.
"""

from isa_definition import INSTRUCTION_FORMAT_DECISION
from register_file import register_file
from fetch_stage import InstructionMemory, FetchStage
from decode_stage import DecodeStage
from execute_stage import ExecuteStage

class Pipeline:
    def __init__(self, instructions):
        """
        instructions: lista de enteros (instrucciones de 32 bits)
        """
        self.rf = register_file()
        self.instr_mem = InstructionMemory(instructions)
        self.fetch = FetchStage(self.rf, self.instr_mem)
        self.decode = DecodeStage(self.rf)
        self.execute = ExecuteStage()
        self.completed = []
        self.cycle = 0

    def step(self):
        """
        Ejecuta un ciclo completo del pipeline: IF → ID → EX
        """
        print(f"\n🔄 Ciclo {self.cycle + 1}")

        # IF: Fetch
        instr = self.fetch.step()
        print(f"→ IF: instrucción = 0x{instr:08x}")

        # ID: Decode
        decoded = self.decode.decode(instr)
        print(f"→ ID: opcode = {decoded['opcode_name']}, formato = {decoded['format_type']}")

        # Leer operandos desde registros
        rs1 = decoded['operandos'].get('rs1')
        rs2 = decoded['operandos'].get('rs2')
        imm = decoded['operandos'].get('imm')

        if rs1 is not None:
            decoded['operandos']['rs1_val'] = self.rf.read(f'R{rs1}')
        if rs2 is not None:
            decoded['operandos']['rs2_val'] = self.rf.read(f'R{rs2}')
        if imm is not None:
            decoded['operandos']['imm'] = imm  # ya es inmediato

        # EX: Execute
        result = self.execute.execute(decoded)
        print(f"→ EX: resultado = {result['result']}, latencia = {result['latency']}")

        # Escribir resultado en registro destino si aplica
        rd = decoded['operandos'].get('rd')
        if rd is not None and result['result'] is not None:
            self.rf.write(f'R{rd}', result['result'])
            print(f"→ WB: R{rd} ← {result['result']}")

        # Guardar instrucción completada
        self.completed.append({
            'instr': instr,
            'decoded': decoded,
            'result': result
        })

        self.cycle += 1

    def run(self, max_cycles=None):
        """
        Ejecuta el pipeline completo hasta agotar instrucciones o alcanzar max_cycles.
        """
        instr_size = INSTRUCTION_FORMAT_DECISION['width_bits'] // 8
        total_instr = len(self.instr_mem.instructions)
        max_cycles = max_cycles or total_instr

        for _ in range(max_cycles):
            try:
                self.step()
            except IndexError:
                print("✅ Fin de instrucciones.")
                break

        print(f"\n📊 Pipeline completado en {self.cycle} ciclos.")
        print("📦 Estado final de registros:")
        for name, value in self.rf.dump_registers().items():
            if name.startswith('R') or name == 'PC':
                print(f"   - {name}: {value}")

    def get_metrics(self):
        return {
            'fetch': self.fetch.get_metrics(),
            'decode': self.decode.get_metrics(),
            'execute': self.execute.get_metrics(),
            'cycles': self.cycle
        }
