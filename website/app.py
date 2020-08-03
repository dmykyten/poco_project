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
from bitarray.util import ba2hex, hex2ba
from bitarray import bitarray
import uuid
import dash_table
from flask import Flask, render_template
import json
import copy
from functools import partial

# Imports from the project
from modules.processor import CPU
from modules.assembler import Assembler, AssemblerError
from website.color_palette_and_layout import table_header, table, button, assembly, background_color, title_color, \
    text_color, not_working, layout, external_stylesheets
from website.example_programs import examples

# CPU DICTIONARY ( key=user.id, value=dict(cpu, intervals) )
user_dict = dict()
# Numbers of buttons (used to change type of isa during cpu creation, are same for every session and user)
buttons = {0: 'risc1', 1: 'risc2', 2: 'risc3', 3: 'cisc'}

# Create app
server = Flask(__name__)
app = dash.Dash(name=__name__, server=server, external_stylesheets=external_stylesheets)
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

            html.Div([
                # Button to assemble
                html.Button('ASSEMBLE', id='assemble', n_clicks=0,
                            style={'margin-left': 50, "color": button['font'],
                                   "background-color": button['background'],
                                   'width': 160, 'display': 'inline-block'}),

                html.Div([
                    dcc.Dropdown(
                        id='example-dropdown',
                        options=[
                            {'label': 'ALPHABET PRINTOUT', 'value': 'alphabet'},
                            {'label': 'HELLO WORLD', 'value': 'hello'},
                        ],
                        placeholder="CHOOSE AN EXAMPLE PROGRAM",
                        style={'width': 200},
                        clearable=False
                    ), ], style={'display': 'inline-block'})

            ]),

            dcc.Link('Need some help?', href='/help', refresh=True)

        ], style={'display': 'inline-block'}),

        # Processor
        html.Div(className='row', children=[

            html.Div([

                # Next instruction
                html.Div(id='instruction', style={'display': 'inline-block', 'margin-right': 10}),

                # Output, registers and flags
                html.Div([

                    html.Div(id='output', style={'display': 'inline-block', 'margin-right': 10}),

                    # Registers
                    html.Div(html.Div(id='registers', children=dash_table.DataTable(id='registers-table',
                                                                                    columns=([{'id': ['SP', 'IP', 'LR',
                                                                                                      'FR', 'R00',
                                                                                                      'R01', 'R02',
                                                                                                      'R03'][i],
                                                                                               'name':
                                                                                                   ['SP', 'IP', 'LR',
                                                                                                    'FR', 'R00', 'R01',
                                                                                                    'R02', 'R03'][
                                                                                                       i] + ': '} for i
                                                                                              in
                                                                                              range(4)]),
                                                                                    data=([{['SP', 'IP', 'LR', 'FR',
                                                                                             'R00', 'R01', 'R02',
                                                                                             'R03'][i]: '0000' for i in
                                                                                            range(4)}]),
                                                                                    editable=True), ),
                             style={'display': 'inline-block', 'margin-right': 10}),

                    html.Div(id='flags', children=dash_table.DataTable(id='flags-table',
                                                                       columns=([{'id': ['CF', 'ZF', 'OF', 'SF'][i],
                                                                                  'name': ['CF', 'ZF', 'OF', 'SF'][
                                                                                              i] + ': '} for i in
                                                                                 range(4)]),
                                                                       data=([{['CF', 'ZF', 'OF', 'SF'][i]: '0' for i in
                                                                               range(4)}]), ),
                             style={'display': 'inline-block', 'margin-right': 10}),

                ], style={'display': 'inline-block'}),

                html.Div([

                    html.Button('SAVE MANUAL CHANGES', id='save-manual', n_clicks=0,
                                style={"color": button['font'],
                                       "background-color": button['background'],
                                       'width': 200, 'display': 'block'}),
                    html.Button('UNDO MANUAL CHANGES', id='undo-manual', n_clicks=0,
                                style={"color": button['font'],
                                       "background-color": button['background'],
                                       'width': 200, 'display': 'block'}),

                ], style={'display': 'inline-block'})

            ]),

            # Memory
            html.Div(id='memory', style={'margin-top': 20, 'margin-bottom': 20}),

            html.Button('NEXT INSTRUCTION', id='next', n_clicks=0,
                        style={"color": button['font'],
                               "background-color": button['background'],
                               'width': 200}),

            html.Button('RUN | STOP', id='run-until-finished', n_clicks=0,
                        style={"color": button['font'],
                               "background-color": button['background'],
                               'width': 200}),

            html.Div
                ([

                dash_table.DataTable(id='seconds',
                                     columns=([{'id': '1', 'name': 'instructions per second'}]),
                                     data=([{'1': '1'}]),
                                     editable=True),

            ],
                style={'display': 'inline-block'}),

        ], style={'display': 'inline-block', 'margin-left': 20}),

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

    # Storage for reaction on 'next instruction' button
    html.Div(id='next-storage', children='0', style={'display': 'none'}),
    # Storage for reaction on 'run until finished' button
    html.Div(id='run-storage', children=dcc.Interval(id='interval', interval=1 * 1000, n_intervals=0, disabled=True),
             style={'display': 'none'}),

    # Example storage (for risc3 by default)
    html.Div(id='examples', children=examples['risc3'], style={'display': 'none'}),

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
@app.callback(Output('id-storage', 'children'),
              [Input('id-creation', 'children')])
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
        user_dict[user_id] = dict()
        user_dict[user_id]['cpu'] = CPU(isa, architecture, io, '')
        user_dict[user_id]['save-manual'] = 0
        user_dict[user_id]['undo-manual'] = 0

    if not assembly_code or assembly_code == "input assembly code here":
        binary_program = hex_program = ''
    else:
        try:
            binary_program = Assembler(isa, assembly_code).binary_code
            user_dict[user_id]['cpu'] = CPU(isa, architecture, io, binary_program)
            hex_program = '\n'.join(list(map(lambda x: hex(int(x, 2)), [x for x in binary_program.split('\n') if x])))

        except AssemblerError as err:
            binary_program = hex_program = f'{err.args[0]}'
            user_dict[user_id]['cpu'] = CPU(isa, architecture, io, '')

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


# Update div with examples
@app.callback(
    Output('examples', 'children'),
    [Input('isa-dropdown', 'value')])
def update_examples(isa):
    return examples[isa]


# Add a chosen example to the textarea
@app.callback(
    Output('input1', 'value'),
    [Input('example-dropdown', 'value'),
     Input('examples', 'children')])
def add_example(example_name, app_examples):
    if example_name == 'alphabet':
        return app_examples[0]
    elif example_name == 'hello':
        return app_examples[1]


# APP CALLBACKS FOR CREATION OF GRAPHIC ELEMENTS OF THE PROCESSOR
@app.callback(Output('instruction', 'children'),
              [Input('instruction-storage', 'children')])
def create_instruction(value):
    """
    # TODO
    :param value:
    :return:
    """
    return dash_table.DataTable(columns=([{'id': '1', 'name': 'NEXT INSTRUCTION'}]),
                                data=([{'1': value}])),


@app.callback(Output('registers', 'children'),
              [Input('registers-storage', 'children')])
def create_registers(value):
    """
    # TODO
    :param value:
    :return:
    """
    regs = []
    values = []
    for i in value:
        regs.append(i.split(' ')[0])
        values.append(i.split(' ')[1])

    return html.Div(dash_table.DataTable(id='registers-table',
                                         columns=([{'id': regs[i], 'name': regs[i]} for i in range(len(regs))]),
                                         data=([{regs[i]: values[i] for i in range(len(regs))}]),
                                         editable=True
                                         ))


@app.callback(Output('flags', 'children'),
              [Input('flags-storage', 'children')])
def create_flags(value):
    """
    # TODO
    :param value:
    :return:
    """
    flags = ['CF', 'ZF', 'OF', 'SF']
    return dash_table.DataTable(id='flags-table',
                                columns=([{'id': flags[i], 'name': flags[i] + ': '} for i in range(len(flags))]),
                                data=([{flags[i]: value[i] for i in range(len(flags))}]), editable=True)


@app.callback(Output('output', 'children'),
              [Input('output-storage', 'children')])
def create_output(value):
    """
    # TODO
    :param value:
    :return:
    """
    return dash_table.DataTable(columns=([{'id': '1', 'name': 'OUTPUT'}]),
                                data=([{'1': value}]),
                                style_table={'width': '150px'}),


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

        # Create a list of dictionaries (key -- column name)
        data = []
        for x in range(len(rows[0])):
            data.append(dict())
            for y in range(len(rows)):
                data[x][headers[y]] = data_lst[x][y]

        return dash_table.DataTable(columns=([{'id': i, 'name': i} for i in headers]),
                                    data=data,
                                    style_table={'height': '300px', 'overflowY': 'auto',
                                                 'background-color': table['background']})


# UPDATE HIDDEN INFO FOR PROCESSOR
@app.callback(Output('next-storage', 'children'),
              [Input('next', 'n_clicks'),
               Input('id-storage', 'children'),
               Input('interval', 'n_intervals')])
def update_next(n_clicks, user_id, interval):
    """
    Return n_clicks for the 'next instruction' button,
    so it changes hidden div, on which graphic elements of
    the processor will react.
    Executes next instruction in the cpu.

    :param n_clicks: n_clicks for the 'next instruction' button
    :param user_id: id of the session/user
    :return: same n_clicks
    """
    if interval > 0:
        if user_id in user_dict:
            user_dict[user_id]['cpu'].web_next_instruction()
        return interval
    if n_clicks > 0:
        if user_id in user_dict:
            user_dict[user_id]['cpu'].web_next_instruction()
        return n_clicks


# Work with intervals
@app.callback(
    Output("interval", "disabled"),
    [Input("run-until-finished", "n_clicks"),
     Input('id-storage', 'children'),
     Input("instruction-storage", "children")],
    [State("interval", "disabled")]
)
def run_interval(n, user_id, instruction, current_state):
    if not n:
        user_dict[user_id]['intervals'] = 0
    if user_id in user_dict:
        if instruction == '0' * len(instruction):
            user_dict[user_id]['intervals'] = n
            return True
        elif n > user_dict[user_id]['intervals']:
            user_dict[user_id]['intervals'] = n
            return not current_state
        else:
            return current_state
    return True


@app.callback(
    Output("interval", "interval"),
    [Input("seconds", "data")]
)
def update_seconds(instructions):
    try:
        int(instructions[0]['1'])
        return 1000 / int(instructions[0]['1'])
    except ValueError:
        return 1 * 1000


@app.callback(Output('instruction-storage', 'children'),
              [Input('next-storage', 'children'),
               Input('id-storage', 'children')])
def update_instruction(value, user_id):
    """
    Reacts on changes in the div, which is
    affected by the 'next instruction' button

    :param value: is not used
    :param user_id: id of the session/user
    :return: string instruction
    """
    if user_id in user_dict:
        return f"{user_dict[user_id]['cpu'].instruction.to01()}"


@app.callback(Output('registers-storage', 'children'),
              [Input('next-storage', 'children'),
               Input('id-storage', 'children'),
               Input('save-manual', 'n_clicks'),
               Input('undo-manual', 'n_clicks')
               ],
              [State('registers-table', 'data')])
def update_registers(value_not_used, user_id, save_manual, undo_manual, data):
    """
    Reacts on changes in the div, which is
    affected by the 'next instruction' button

    :param value_not_used: is not used
    :param user_id: id of the session/user
    :return: string registers
    """
    if user_id in user_dict:
        if save_manual > user_dict[user_id]['save-manual']:
            user_dict[user_id]['save-manual'] = save_manual
            new_reg_dict = data[0]
            for key, value in new_reg_dict.items():
                user_dict[user_id]['cpu'].registers[key[:-1]]._state = hex2ba(value)

        elif undo_manual > user_dict[user_id]['undo-manual']:
            user_dict[user_id]['undo-manual'] = undo_manual

        items = [(value.name, value._state.tobytes().hex()) for key, value in
                 user_dict[user_id]['cpu'].registers.items()]
        values = []
        for i in range(len(items)):
            values.append(f"{(items[i][0] + ':')} {items[i][1]}")
        return values


@app.callback(Output('flags-storage', 'children'),
              [Input('next-storage', 'children'),
               Input('id-storage', 'children'),
               Input('save-manual', 'n_clicks'),
               Input('undo-manual', 'n_clicks')
               ],
              [State('flags-table', 'data')])
def update_flags(value, user_id, save_manual, undo_manual, data):
    """
    Reacts on changes in the div, which is
    affected by the 'next instruction' button
    # TODO: about manual

    :param value: is not used
    :param user_id: id of the session/user
    :return: string flags
    """
    if user_id in user_dict:
        if save_manual > user_dict[user_id]['save-manual']:
            user_dict[user_id]['save-manual'] = save_manual
            cf, zf, of, sf = data[0]['CF'], data[0]['ZF'], data[0]['OF'], data[0]['SF'],
            user_dict[user_id]['cpu'].registers['FR']._state[12:16] = bitarray(''.join([cf, zf, of, sf]))

            return [cf, zf, of, sf]
        elif undo_manual > user_dict[user_id]['undo-manual']:
            user_dict[user_id]['undo-manual'] = undo_manual
            cf, zf, of, sf = list(user_dict[user_id]['cpu'].registers['FR']._state.to01()[12:])

            return [cf, zf, of, sf]
        else:
            return list(user_dict[user_id]['cpu'].registers['FR']._state.to01()[-4:])


@app.callback(Output('output-storage', 'children'),
              [Input('next-storage', 'children'),
               Input('id-storage', 'children')])
def update_output(value, user_id):
    """
    Reacts on changes in the div, which is
    affected by the 'next instruction' button

    :param value: is not used
    :param user_id: id of the session/user
    :return: string output
    """
    if user_id in user_dict:
        shell_slots = []
        for port, device in user_dict[user_id]['cpu'].ports_dictionary.items():
            shell_slots.append(str(device))
        return " ".join(shell_slots)


@app.callback(Output('memory-storage', 'children'),
              [Input('next-storage', 'children'),
               Input('id-storage', 'children')])
def update_memory(value, user_id):
    """
    Reacts on changes in the div, which is
    affected by the 'next instruction' button

    :param value: is not used
    :param user_id: id of the session/user
    :return: string memory
    """
    if user_id in user_dict:
        memory_data = [[], [], [], [], [], [], [], []]
        for i in range(0, len(user_dict[user_id]['cpu'].data_memory.slots), 32 * 8):
            string = ba2hex(user_dict[user_id]['cpu'].data_memory.slots[i:i + 32 * 8])
            for x in range(8):
                memory_data[x].append(" ".join([string[8 * x:8 * x + 8][y:y + 2] for y in range(0, 8, 2)]))
        lst = []
        for i in memory_data:
            lst.append('\t'.join(i))
        return ['\n'.join(lst), '']


# HELP PAGE
@app.server.route('/help')
def template_test():
    with open("docs/help.json", "r") as file:
        help_dict = json.load(file)
    with open("modules/registers.json", "r") as file:
        register_dict = json.load(file)["risc3"]

    p_style = "color: #FFFFFF; padding-left: 12%; width: 75%"
    return render_template('help.html', items=help_dict, p_style=p_style, reg_dict=register_dict)


# Run the program
if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)
# TODO:
#  cookies to save previous program,
#  edit memory,
#  change memory slots (numeration????????),
#  add new version to server,
#  make table undraggable,
#  fix table becoming dark,
#  documentation
