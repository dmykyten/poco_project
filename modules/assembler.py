#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Assembly Simulator project 2020
# GNU General Public License v3.0

import os
import json
import argparse
from collections import defaultdict

from modules.functions import twos_complement


class Assembler:
    """
    Assembler class. Takes a file and specified architecture type as
    an input, and translates to binary code
    """

    def __init__(self):
        """ Initializes the assembler, outputs the binary code file"""

        # Creating the command line parser and main arguments
        parser = argparse.ArgumentParser()
        parser.add_argument("-f","--file", help="provide the assembly program filepath")
        parser.add_argument("--isa", help="specify the ISA architecture: RISC1 (Stack), "
                                 "RISC2 (Accumulator), RISC3 (Register), CISC (Register)")
        parser.add_argument("-o", "--output", help="Specify the output file")

        # Parsing the command line arguments
        args = parser.parse_args()

        # Check if the assembly program file was provided
        if not args.file:
            raise AssemblerError("Assembly program filepath not provided")

        # Check if the ISA is provided and actually exists
        valid_isa = ['risc1', 'risc2', 'risc3', 'cisc']
        if not args.isa or args.isa.lower() not in valid_isa:
            raise AssemblerError("Specify the valid instruction set architecture")

        # Read the program text
        with open(args.file, "r") as file:
            program_text = file.read()

        # Open the list of instructions for this architecture and reformat it for our purposes
        # DefaultDict allows to have several values for the same key all pushed into type specified - we use list
        # This is useful since we might have the same assembly instruction encoded differently depending on the operands
        with open(os.path.join("modules", "instructions.json"), "r") as file:
            self.instructions = defaultdict(list)
            for opcode, details in json.load(file)[args.isa.lower()].items():
                self.instructions[details[0]].append([opcode, details[1]])

        # Open the list of registers for this architecture and format it properly
        with open(os.path.join("modules", "registers.json"), "r") as file:
            registers = json.load(file)[args.isa.lower()]
            self.register_names = {register[0]: register[2] for register in registers}

        # Determining the size of the instructions to read
        instruction_sizes = {"risc1": (6, 6), "risc2": (8, 8), "risc3": (16, 6), "cisc": (8, 8)}
        self.instruction_size = instruction_sizes[args.isa.lower()]

        binary_code = self.translate(program_text)

        # If there was an output path provided, save the binary code there
        if args.output:
            output_path = args.output

        # If there was no output path provided, save the binary code in the
        # same folder as the assembly program with a different file extension
        else:
            output_path = os.path.join(os.path.dirname(args.file),
                                       os.path.splitext(os.path.basename(args.file))[0]+".bin")

        with open(output_path, "w") as file:
            file.write(binary_code)

    def translate(self, text):
        """
        Translates the assembly code into binary code
        :param text: str - assembly code
        """
        binary_code = ""

        # Divide the program into lines
        for line in text.split("\n"):

            # Split instruction name and operands
            binary_line = ""
            arguments = line.split(" ")
            assembly_instruction, operands = arguments[0], arguments[1:]

            for ind, operand in enumerate(operands[:-1]):
                if not operand.endswith(','):
                    raise AssemblerError("Provide valid operands for this instruction (commas included)")
                operands[ind] = operand[:-1]

            # Check if the instruction actually exists for this architecture
            if assembly_instruction not in self.instructions:
                raise AssemblerError("Not valid opcode")

            # Get the list of encodings for this assembly instruction
            instructions_info = self.instructions[assembly_instruction]

            # If this assembly instruction has only one encoding, encode it and its operands
            if len(instructions_info) == 1:
                binary_line = self.__encode_operands(operands, instructions_info[0])
            else:

                # If this assembly instruction has a few different opcodes depending on the type of operands
                # we check every possible option until we find the one we needed
                for instruction_info in instructions_info:
                    try:

                        # Low and High byte moves have 5-bit opcodes, a special case
                        if assembly_instruction in ["mov_low", "mov_high"] and len(instruction_info[0]) != 5:
                            instruction_info[0] = instruction_info[0][:-1]

                        binary_line = self.__encode_operands(operands, instruction_info)
                        break
                    except AssemblerError:
                        continue

                # If all of the opcode options were wrong, raise the error
                if not binary_line:
                    raise AssemblerError("Provide valid operands for this instruction")

            binary_code += binary_line + "\n"

        return binary_code

    def __encode_operands(self, operands, instruction_info):
        """
        Encodes the operands given an opcode and operands types
        :param operands: list - list of operands-strings
        :param instruction_info: list - of instruction encoding and operand types
        """
        binary_line = instruction_info[0]
        types = instruction_info[1]

        if len(operands) != len(types):
            raise AssemblerError("Provide valid operands for this instruction")

        # Check if the operand provided is of the type needed, if yes, encode and add it to the current line
        for index, operand in enumerate(operands):
            if self.__valid_type(operand, op_type:=types[index]):

                # Encode the operand properly and add it to the line
                if op_type == "reg":
                    binary_line += self.register_names[operand[1:]]
                elif op_type == "memreg":
                    binary_line += self.register_names[operand[2:-1]]
                elif op_type.startswith("imm"):
                    num = int(operand[1:])
                    bit_len = int(op_type[3:])

                    if not (-1*2**(bit_len-1) < num < 2**(bit_len-1)):
                        raise AssemblerError("Immediate constant provided too big")

                    binary_line += bin(twos_complement(num, bit_len))[2:].rjust(int(op_type[3:]), '0')

            else:
                raise AssemblerError("Provide valid operands for this instruction")

        return binary_line.ljust(self.instruction_size[0], '0')

    def __valid_type(self, assembly_op, op_type):
        """
        Checks if the operand provided in assembly code is of valid type for this instruction
        """
        # If the operand signifies a register, it should start
        # with a '%' sign and the name should exist in this architecture
        if op_type == "reg":
            return assembly_op.startswith("%") and assembly_op[1:] in self.register_names

        # If the operand is an immediate constant, it should start with a '$' sign and contain numbers only
        elif op_type.startswith("imm"):
            return assembly_op.startswith("$") and self.__is_number(assembly_op[1:])

        # If the operand is a memory location addressed by a register, it shoould look like [%reg]
        elif op_type == "memreg":
            return (assembly_op.startswith("[") and assembly_op.endswith("]")
                    and self.__valid_type(assembly_op[1:-1], "reg"))

    @staticmethod
    def __is_number(n):
        """
        Checks if the number string provided is valid
        :param n: str
        :return: bool
        """
        try:
            int(n)
            return True
        except ValueError:
            return False


class AssemblerError(Exception):
    """ Error raised by the assembler module """


if __name__ == '__main__':
    assembler = Assembler()