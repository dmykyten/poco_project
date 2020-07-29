#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Assembly Simulator project 2020
# GNU General Public License v3.0

import time
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from bitarray.util import ba2hex
import uuid
import dash_table

# Imports from the project
from modules.processor import CPU
from modules.assembler import Assembler, AssemblerError
from website.color_palette_and_layout import table_header, table, button, assembly, background_color, title_color, \
    text_color, not_working, layout, external_stylesheets

# CPU DICTIONARY ( key=user.id, value=[cpu, buttons list (number of clicks)] )
user_dict = dict()
# Numbers of buttons (used to change type of isa during cpu creation, are same for every session and user)
buttons = {0: 'risc1', 1: 'risc2', 2: 'risc3', 3: 'cisc'}

# Create app
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "ASSEMBLY SIMULATOR"

# MAIN LAYOUT
app.layout = html.Div([

    # "MAIN MENU"
    html.Div([
        # Title
        dcc.Markdown("ASSEMBLY SIMULATOR",
                     style={'color': title_color, 'font-family': "Roboto Mono, monospace",
                            'font-size': '25px', 'display': 'inline-block'}),

        # Dropdowns for isa, architecture and i/o mode
        html.Div([

            html.Div([

                dcc.Dropdown(
                    id='isa-dropdown',
                    options=[
                        {'label': 'REGISTER RISC', 'value': 'risc3'},
                        {'label': 'REGISTER CISC', 'value': 'cisc', 'disabled': True},
                        {'label': 'STACK', 'value': 'risc1'},
                        {'label': 'ACCUMULATOR', 'value': 'risc2'},
                    ],
                    value='risc3',
                    style={'width': 200},
                    clearable=False,
                ),
            ], style={'display': 'inline-block'}),

            html.Div([

                dcc.Dropdown(
                    id='architecture-dropdown',
                    options=[
                        {'label': 'VON NEUMANN', 'value': 'neumann'},
                        {'label': 'HARVARD', 'value': 'harvard', 'disabled': True},
                    ],
                    value='neumann',
                    style={'width': 200},
                    clearable=False,
                ),

            ], style={'display': 'inline-block'}),

            html.Div([

                dcc.Dropdown(
                    id='io-dropdown',
                    options=[
                        {'label': 'MEMORY-MAPPED', 'value': 'mmio', 'disabled': True},
                        {'label': 'SPECIAL COMMANDS', 'value': 'special'},
                    ],
                    value='special',
                    style={'width': 200},
                    clearable=False,
                ),

            ], style={'display': 'inline-block'}),

        ], style={'display': 'inline-block', 'margin-left': 600}),
    ]),

    # ASSEMBLER AND PROCESSOR
    html.Div([

        # Assembler
        html.Div([

            html.Div([

                # Textarea for input of assembly code
                dcc.Textarea(id="input1", spellCheck='false', value="input assembly code here",
                             style={'width': 235, 'height': 400, 'display': 'inline-block',
                                    "color": assembly['font'], 'font-size': '15px',
                                    "background-color": assembly['background'],
                                    'font-family': "Roboto Mono, monospace"},
                             autoFocus='true'),

                # Tabs with bin and hex code
                html.Div([
                    dcc.Tabs(id='TABS', value='tabs', children=[
                        dcc.Tab(label='BIN', value='binary'),
                        dcc.Tab(label='HEX', value='hexadecimal'),
                    ], style={'width': 185, 'height': 50}),
                    html.Div(id='tabs-content')
                ], style={'display': 'inline-block'}),

            ]),

            # Button to assemble
            html.Button('ASSEMBLE', id='assemble', n_clicks=0,
                        style={'margin-left': 50, "color": button['font'],
                               "background-color": button['background'],
                               'width': 160})

        ], style={'display': 'inline-block'}),

        # Processor
        html.Div([

            html.Div([

                # Next instruction
                html.Div(id='instruction', style={'display': 'inline-block'}),

                # Registers
                html.Div(id='registers', style={'display': 'inline-block'}),

                # Flags and output
                html.Div([

                    html.Div(id='flags', style={'display': 'inline-block'}),

                    html.Div(id='output', style={'display': 'inline-block'}),

                ], style={'display': 'inline-block'}),

            ]),

            # Memory
            html.Div(id='memory'),

        ], style={'display': 'inline-block'}),

    ]),

    # HIDDEN DIVS

    # Main info (has default settings)
    html.Div(id="info", children='risc3 neumann special', style={'display': 'none'}),
    # Id creation and storage
    html.Div(id='id-storage', style={'display': 'none'}),
    html.Div(id='id-creation', style={'display': 'none'}),
    # Binary and hexadecimal code translations storage
    html.Div(id='code', children=['', ''], style={'display': 'none'}),
    # Instruction storage
    html.Div(id='instruction-storage', children='0' * 16, style={'display': 'none'}),
    # Memory storage (in a list, because Harvard architecture has two separate memories)
    html.Div(id='memory-storage', children=['\n'.join(['\t'.join(['00 00 00 00'] * 32)] * 8), ''],
             style={'display': 'none'}),
    # Registers storage (first element –– registers, second –– their values )
    html.Div(id='registers-storage',
             children=[' '.join(['SP', 'IP', 'LR', 'FR', 'R00', 'R01', 'R02', 'R03']), ' '.join(['0000'] * 8)],
             style={'display': 'none'}),
    # Flags storage
    html.Div(id='flags-storage', children=['0'] * 4, style={'display': 'none'}),
    # Output storage
    html.Div(id='output-storage', children='', style={'display': 'none'}),
])


# APP CALLBACKS FOR INPUT/OUTPUT OF THE INFORMATION, ASSEMBLER
# Change main info
@app.callback(
    Output('info', 'children'),
    [Input('isa-dropdown', 'value'),
     Input('architecture-dropdown', 'value'),
     Input('io-dropdown', 'value')])
def update_output(isa, arch, io):
    """
    Update main information about the cpu,
    depending on the choice from dropdowns.

    :param isa: chosen isa
    :param arch: chosen architecture
    :param io: chosen I/O mode
    :return: string with information
    """
    return ' '.join([isa, arch, io])


# Create user id
@app.callback(Output('id-storage', 'children'), [Input('id-creation', 'children')])
def get_ip(value):
    """
    Return randomly generated id each time new session starts

    :param value: is not used (is here by default)
    :return: random id
    """
    session_id = str(uuid.uuid4())
    return session_id


# Save binary and hexadecimal code
@app.callback(Output('code', 'children'),
              [Input('assemble', 'n_clicks'),
               Input('info', 'children'),
               Input('id-storage', 'children')],
              [State('input1', 'value')])
def assemble(n_clicks, info, user_id, assembly_code):
    """
    Translate input assembly code to binary and hexadecimal ones.

    :param n_clicks: is not used (is here by default)
    :param info: isa, architecture and I/O mode
    :param user_id: id of the session/user
    :param assembly_code: input assembly code
    :return: binary and hexadecimal codes or assembler error
    """
    isa, architecture, io = info.split()

    global user_dict
    if user_id not in user_dict:
        user_dict[user_id] = CPU(isa, architecture, io, '')

    if not assembly_code or assembly_code == "input assembly code here":
        binary_program = hex_program = ''
    else:
        try:
            binary_program = Assembler(isa, assembly_code).binary_code
            user_dict[user_id] = CPU(isa, architecture, io, binary_program)
            hex_program = '\n'.join(list(map(lambda x: hex(int(x, 2)), [x for x in binary_program.split('\n') if x])))

        except AssemblerError as err:
            binary_program = hex_program = f'{err.args[0]}'
            user_dict[user_id] = CPU(isa, architecture, io, '')

    return binary_program, hex_program


# Create tabs content (bin and hex)
@app.callback(Output('tabs-content', 'children'),
              [Input('TABS', 'value'),
               Input('code', 'children')])
def render_content_hex_bin(tab, code_lst):
    """
    Render two tabs: with binary and with hexadecimal code translations

    :param tab: one of two: binary or hexadecimal
    :param code_lst: list with binary and with hexadecimal code translations
    :return: tabs
    """
    if tab == 'binary':
        return html.Div([
            dcc.Textarea(value=code_lst[0],
                         style={'width': 185, 'height': 400, "color": assembly['font'], 'font-size': '15px',
                                "background-color": assembly['background'], 'font-family': "Roboto Mono, monospace"},
                         disabled=True)
        ])
    elif tab == 'hexadecimal':
        return html.Div([
            dcc.Textarea(value=code_lst[1],
                         style={'width': 185, 'height': 400, "color": assembly['font'], 'font-size': '15px',
                                "background-color": assembly['background'], 'font-family': "Roboto Mono, monospace"},
                         disabled=True)
        ])
    else:
        return html.Div([
            dcc.Textarea(value=code_lst[0],
                         style={'width': 185, 'height': 400, "color": assembly['font'], 'font-size': '15px',
                                "background-color": assembly['background'], 'font-family': "Roboto Mono, monospace"},
                         disabled=True)
        ])


# UPDATE HIDDEN INFO FOR PROCESSOR

# APP CALLBACKS FOR CREATION OF GRAPHIC ELEMENTS OF THE PROCESSOR
@app.callback(Output('instruction', 'children'),
              [Input('instruction-storage', 'children')])
def create_instruction(value):
    """
    # TODO
    :param value:
    :return:
    """
    return dcc.Textarea(value=value, disabled=True)


@app.callback(Output('registers', 'children'),
              [Input('registers-storage', 'children')])
def create_registers(value):
    """
    # TODO
    :param value:
    :return:
    """
    return dcc.Textarea(value=str(value))


@app.callback(Output('flags', 'children'),
              [Input('flags-storage', 'children')])
def create_flags(value):
    """
    # TODO
    :param value:
    :return:
    """
    return dcc.Textarea(value=str(value))


@app.callback(Output('output', 'children'),
              [Input('output-storage', 'children')])
def create_output(value):
    """
    # TODO
    :param value:
    :return:
    """
    return dcc.Textarea(value=value, disabled=True)


@app.callback(Output('memory', 'children'),
              [Input('memory-storage', 'children')])
def create_memory(value):
    """
    # TODO
    :param value:
    :return:
    """
    if not value[1]:
        headers = ["Addr   :  "]
        for i in range(0, 32, 4):
            headers.append(f"{hex(i)[2:].rjust(2, '0')} {hex(i + 1)[2:].rjust(2, '0')} "
                           f"{hex(i + 2)[2:].rjust(2, '0')} {hex(i + 3)[2:].rjust(2, '0')}")

        rows = []
        for i in range(0, 1024, 32):
            rows.append(hex(i)[2:].rjust(8, "0"))

        temp_lst1 = value[0].split('\n')
        memory_data = []
        for i in temp_lst1:
            memory_data.append(i.split('\t'))

        rows = [rows] + memory_data

        data_lst = []
        for y in range(len(rows[0])):
            data_lst.append([])
            for x in range(len(rows)):
                data_lst[y].append(rows[x][y])

        data = []
        for x in range(len(rows[0])):
            data.append(dict())
            for y in range(len(rows)):
                data[x][headers[y]] = data_lst[x][y]

        return dash_table.DataTable(columns=([{'id': i, 'name': i} for i in headers]),
                                    data=data,
                                    style_table={'height': '300px', 'overflowY': 'auto'})


# [{'Model': 1, 'Weight': 0, 'Torque': 0, 'Width': 0, 'Height': 0, 'Efficiency': 0, 'Power': 0, 'Displacement': 0},
#  {'Model': 2, 'Weight': 0, 'Torque': 0, 'Width': 0, 'Height': 0, 'Efficiency': 0, 'Power': 0, 'Displacement': 0},
#  {'Model': 3, 'Weight': 0, 'Torque': 0, 'Width': 0, 'Height': 0, 'Efficiency': 0, 'Power': 0, 'Displacement': 0},
#  {'Model': 4, 'Weight': 0, 'Torque': 0, 'Width': 0, 'Height': 0, 'Efficiency': 0, 'Power': 0, 'Displacement': 0}]
# Run the program
if __name__ == '__main__':
    # SERVER LAUNCH
    dev_server = app.run_server
    app.run_server(debug=True, threaded=True)

# TODO: help page,
#  add program examples,
#  cookies to save previous program,
#  edit memory and registers,
#  make next execute till the program is not finished (additional button, user can choose seconds),
#  change memory slots,
#  add new version to server,
#  add bitwise flag,
#  make table undraggable
