
import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa_assembler')))



import os
from text_to_hex import convert_txt_to_hex

convert_txt_to_hex("lorem.txt", "lorem.hex")

print("Contenido de lorem.hex:")
with open("lorem.hex", "r", encoding="utf-8") as f:
    print(f.read())
