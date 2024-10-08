import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from PIL import Image, ImageTk
import json
import os
import serial
import serial.tools.list_ports
import struct
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from datetime import datetime
import numpy as np


# Funções para carregar e salvar usuários
def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r') as file:
            return json.load(file)
    return {}


def save_users(users):
    with open('users.json', 'w') as file:
        json.dump(users, file)


# Função para calcular o checksum
def calculate_checksum(data):
    return sum(data) & 0xFF


# Função para ler dados de aceleração
def read_acceleration_data(serial_port):
    try:
        if serial_port.in_waiting > 0:
            data = serial_port.read(serial_port.in_waiting)
            while data:
                if data[0] == 0x55:
                    if len(data) >= 11:
                        data_type = data[1]
                        if data_type == 0x51:
                            payload = data[2:10]
                            sum_check = data[10]


                            if calculate_checksum([0x55, 0x51] + list(payload)) == sum_check:
                                AxL, AxH, AyL, AyH, AzL, AzH, TL, TH = struct.unpack('<8B', payload)


                                ax_raw = (AxH << 8) | AxL
                                ay_raw = (AyH << 8) | AyL
                                az_raw = (AzH << 8) | AzL


                                ax = ax_raw if ax_raw < 0x8000 else ax_raw - 0x10000
                                ay = ay_raw if ay_raw < 0x8000 else ay_raw - 0x10000
                                az = az_raw if az_raw < 0x8000 else az_raw - 0x10000


                                ax = ax / 32768.0 * 16 * 9.8
                                ay = ay / 32768.0 * 16 * 9.8
                                az = az / 32768.0 * 16 * 9.8


                                return ax, ay, az


                            data = data[11:]
                        else:
                            data = data[1:]
                    else:
                        data = data[1:]
                else:
                    data = data[1:]


        return None, None, None
    except Exception as e:
        print(f"Erro ao ler os dados: {e}")
        return None, None, None
def read_register(ser, address):
    command = bytes([0xFF, 0xAA, address, 0x00])
    ser.write(command)
    time.sleep(0.01)  # Tempo de espera
    response = ser.read(10)
    
    print(f"Resposta recebida (tamanho {len(response)}): {response.hex()}")
    return response

def is_valid_response(response):
    return len(response) == 10  # Exemplo: checa apenas o tamanho

def extract_quaternion(response):
    try:
        q0 = struct.unpack('<h', response[2:4])[0] / 32768.0
        q1 = struct.unpack('<h', response[4:6])[0] / 32768.0
        q2 = struct.unpack('<h', response[6:8])[0] / 32768.0
        q3 = struct.unpack('<h', response[8:10])[0] / 32768.0
        return (q0, q1, q2, q3)
    except Exception as e:
        print(f"Erro ao extrair quaternions: {e}")
        return None

def read_quaternion(ser):
    response = read_register(ser, 0x2C)
    
    if is_valid_response(response):
        quaternion = extract_quaternion(response)
        if quaternion:
            return quaternion
        else:
            print("Erro ao extrair quaternion.")
    else:
        print("Resposta inválida ou não contém dados de quaternion.")
    return None


class LoginApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Login")
        self.master.geometry("700x400")

        # Adicionar imagem de fundo
        current_dir = os.path.dirname(os.path.abspath(__file__))  # Obtém o diretório do script
        image_path = os.path.join(current_dir, 'LIPS-Fundo_branco.png')  # Cria o caminho da imagem
        self.bg_image = Image.open(image_path)  # Carrega a imagem
        self.bg_image = self.bg_image.resize((125, 75), Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        self.bg_label = tk.Label(master, image=self.bg_photo)
        self.bg_label.place(relx=0.95, rely=0.95, anchor='se')

        # Alterar cores
        self.entry_bg = '#F0F0F0'
        self.btn_color = '#0056b3'


        # Criar um Frame para a caixa de login
        self.login_frame = tk.Frame(master, bg=self.entry_bg, bd=2, relief='groove')
        self.login_frame.place(relx=0.5, rely=0.5, anchor='center', width=215, height=275)


        # Widgets de login
        self.username_label = tk.Label(self.login_frame, text="Usuário", font=('Arial', 14))
        self.username_label.grid(row=0, column=0, padx=10, pady=10)
        self.username_entry = tk.Entry(self.login_frame, font=('Arial', 12), highlightthickness=0, bg=self.entry_bg)
        self.username_entry.grid(row=1, column=0, padx=10, pady=5)


        self.password_label = tk.Label(self.login_frame, text="Senha", font=('Arial', 14))
        self.password_label.grid(row=2, column=0, padx=10, pady=10)
        self.password_entry = tk.Entry(self.login_frame, font=('Arial', 12), show="*", highlightthickness=0, bg=self.entry_bg)
        self.password_entry.grid(row=3, column=0, padx=10, pady=5)


        self.login_button = tk.Button(self.login_frame, text="Login", font=('Arial', 12), command=self.check_login, bg=self.btn_color, fg='white')
        self.login_button.grid(row=4, column=0, padx=10, pady=10)


        self.register_button = tk.Button(self.login_frame, text="Registrar", font=('Arial', 12), command=self.open_register, bg=self.btn_color, fg='white')
        self.register_button.grid(row=5, column=0, padx=10, pady=10)


        # Rodapé com nomes dos desenvolvedores
        self.footer_label = tk.Label(master, text="Desenvolvedores: João Schriefer, Lucas Gabriel, João Pedro, Davi Lara", font=('Arial', 10), bg='#FFFFFF', fg='#555555')
        self.footer_label.place(relx=0.5, rely=0.95, anchor='center')


    def check_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        users = load_users()


        if username in users and users[username] == password:
            messagebox.showinfo("Login", "Login realizado com sucesso!")
            self.master.destroy()  # Fecha a janela de login
            self.open_app()
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos.")


    def open_register(self):
        register_window = tk.Toplevel(self.master)
        RegisterApp(register_window)


    def open_app(self):
        root = tk.Tk()
        app = AccelerometerApp(root)
        root.mainloop()


class RegisterApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Registrar")
        self.master.geometry("400x400")


        self.username_label = tk.Label(master, text="Usuário:", font=('Impact', 10))
        self.username_label.pack(pady=10)


        self.username_entry = tk.Entry(master)
        self.username_entry.pack(pady=10)


        self.password_label = tk.Label(master, text="Senha:", font=('Impact', 10))
        self.password_label.pack(pady=10)


        self.password_entry = tk.Entry(master, show="*")
        self.password_entry.pack()


        self.register_button = tk.Button(master, text="Registrar", font=('Impact', 10), command=self.register)
        self.register_button.pack(pady=10)


    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        users = load_users()


        if username in users:
            messagebox.showerror("Erro", "Usuário já existe.")
        else:
            users[username] = password
            save_users(users)
            messagebox.showinfo("Registro", "Usuário registrado com sucesso.")
            self.master.destroy()


class AccelerometerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Leitor de Acelerômetro")


        # Configurações iniciais
        self.serial_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.serial_port1 = serial.Serial(self.serial_ports[0], 115200)
        self.serial_port2 = serial.Serial(self.serial_ports[1], 115200)


        self.data1 = []
        self.data2 = []
        self.quaternion_data1 = []
        self.quaternion_data2 = []
        self.oscillation_data = []


        self.frequency1 = 0
        self.frequency2 = 0
        self.last_time1 = time.time()
        self.last_time2 = time.time()


        self.last_export_time = time.time()
        self.start_time = time.time()
        self.running = True
        self.data_interval = 10  # Intervalo de atualização de dados em ms


        self.file_name = self.ask_file_name()
        self.create_excel_file()


        # Criar abas
        self.tab_control = ttk.Notebook(master)
        self.tab1 = ttk.Frame(self.tab_control)
        self.tab2 = ttk.Frame(self.tab_control)
        self.tab3 = ttk.Frame(self.tab_control)


        self.tab_control.add(self.tab1, text='Acelerômetro 1')
        self.tab_control.add(self.tab2, text='Acelerômetro 2')
        self.tab_control.add(self.tab3, text='Oscilação')
        self.tab_control.pack(expand=1, fill='both')


        # Gráficos
        self.fig1, self.ax1 = plt.subplots()
        self.canvas1 = FigureCanvasTkAgg(self.fig1, self.tab1)
        self.canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)


        self.fig2, self.ax2 = plt.subplots()
        self.canvas2 = FigureCanvasTkAgg(self.fig2, self.tab2)
        self.canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)


        self.fig3, self.ax3 = plt.subplots()
        self.canvas3 = FigureCanvasTkAgg(self.fig3, self.tab3)
        self.canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)


        # Labels para frequência
        self.freq_label1 = tk.Label(self.tab1, text=f'Frequência: {self.frequency1:.2f} Hz', font=('Helvetica', 12))
        self.freq_label1.pack(pady=5)


        self.freq_label2 = tk.Label(self.tab2, text=f'Frequência: {self.frequency2:.2f} Hz', font=('Helvetica', 12))
        self.freq_label2.pack(pady=5)


        self.update_data()


    def ask_file_name(self):
        return simpledialog.askstring("Nome do Arquivo", "Digite o nome do arquivo Excel:")


    def create_excel_file(self):
        self.df = pd.DataFrame(columns=['Data Hora', 'Ax1', 'Ay1', 'Az1', 'Oscilação1', 'Frequência1',
                                        'Ax2', 'Ay2', 'Az2', 'Oscilação2', 'Frequência2'])


    def update_data(self):
        if not self.running:
            return

        start_time = time.time()  # Inicia o tempo para monitorar a duração da função
        ax1, ay1, az1 = read_acceleration_data(self.serial_port1)
        ax2, ay2, az2 = read_acceleration_data(self.serial_port2)
        quaternion1 = read_quaternion(self.serial_port1)
        quaternion2 = read_quaternion(self.serial_port2)


        current_time = time.time()
        if quaternion1:
            self.quaternion_data1.append(quaternion1)
        if quaternion2:
            self.quaternion_data2.append(quaternion2)

        if ax1 is not None and ax2 is not None:
            self.data1.append((ax1, ay1, az1))
            self.data2.append((ax2, ay2, az2))


            oscillation1 = np.sqrt(ax1**2 + ay1**2 + az1**2)
            oscillation2 = np.sqrt(ax2**2 + ay2**2 + az2**2)
            self.oscillation_data.append((oscillation1, oscillation2))


            # Cálculo da frequência
            time_diff1 = current_time - self.last_time1
            time_diff2 = current_time - self.last_time2
            self.last_time1 = current_time
            self.last_time2 = current_time


            if time_diff1 > 0:
                self.frequency1 = 1 / time_diff1
            if time_diff2 > 0:
                self.frequency2 = 1 / time_diff2


            # Limitar a 100 entradas
            if len(self.data1) >= 100:
                self.data1 = []  # Limpa os dados ao atingir 100
            if len(self.data2) >= 100:
                self.data2 = []  # Limpa os dados ao atingir 100
            if len(self.oscillation_data) >= 100:
                self.oscillation_data = []  # Limpa os dados ao atingir 100


            # Atualizando gráficos
            self.ax1.clear()
            self.ax1.plot(range(len(self.data1)), [d[0] for d in self.data1], color='red', label='X')
            self.ax1.plot(range(len(self.data1)), [d[1] for d in self.data1], color='green', label='Y')
            self.ax1.plot(range(len(self.data1)), [d[2] for d in self.data1], color='blue', label='Z')
            self.ax1.set_xlim(0, 100)
            self.ax1.set_ylim(-20, 20)
            self.ax1.set_title('Acelerômetro 1')
            self.ax1.legend()


            self.ax2.clear()
            self.ax2.plot(range(len(self.data2)), [d[0] for d in self.data2], color='red', label='X')
            self.ax2.plot(range(len(self.data2)), [d[1] for d in self.data2], color='green', label='Y')
            self.ax2.plot(range(len(self.data2)), [d[2] for d in self.data2], color='blue', label='Z')
            self.ax2.set_xlim(0, 100)
            self.ax2.set_ylim(-20, 20)
            self.ax2.set_title('Acelerômetro 2')
            self.ax2.legend()


            if self.oscillation_data:
                max_oscillation1 = max(o[0] for o in self.oscillation_data)
                max_oscillation2 = max(o[1] for o in self.oscillation_data)
                max_oscillation = max(max_oscillation1, max_oscillation2)


                self.ax3.clear()
                self.ax3.plot(range(len(self.oscillation_data)), [o[0] for o in self.oscillation_data], color='red', label='Oscilação 1')
                self.ax3.plot(range(len(self.oscillation_data)), [o[1] for o in self.oscillation_data], color='green', label='Oscilação 2')
                self.ax3.set_xlim(0, 100)
                self.ax3.set_ylim(0, max_oscillation + 1)
                self.ax3.set_title('Oscilação')
                self.ax3.legend()

            # Exportar dados
            if current_time - self.last_export_time >= 0.3:  # 300 ms
                self.export_data(ax1, ay1, az1, oscillation1, self.frequency1,
                                ax2, ay2, az2, oscillation2, self.frequency2,
                                quaternion1, quaternion2)
                self.last_export_time = current_time

            # Verificar tempo para o teste
            if current_time - self.start_time >= 300:  # 5 minutos
                self.end_test()


        # Atualiza os textos de frequência
        self.freq_label1.config(text=f'Frequência: {self.frequency1:.2f} Hz')
        self.freq_label2.config(text=f'Frequência: {self.frequency2:.2f} Hz')


        self.canvas1.draw()
        self.canvas2.draw()
        self.canvas3.draw()

        elapsed_time = time.time() - start_time
        print(f"Tempo gasto na função update_data: {elapsed_time:.3f} segundos")

        self.master.after(self.data_interval, self.update_data)


    def export_data(self, ax1, ay1, az1, oscillation1, frequency1, ax2, ay2, az2, oscillation2, frequency2,
                    quaternion1=None, quaternion2=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = pd.DataFrame([[timestamp, ax1, ay1, az1, oscillation1, frequency1,
                                  ax2, ay2, az2, oscillation2, frequency2,
                                  quaternion1[0] if quaternion1 else None,
                                  quaternion1[1] if quaternion1 else None,
                                  quaternion1[2] if quaternion1 else None,
                                  quaternion1[3] if quaternion1 else None,
                                  quaternion2[0] if quaternion2 else None,
                                  quaternion2[1] if quaternion2 else None,
                                  quaternion2[2] if quaternion2 else None,
                                  quaternion2[3] if quaternion2 else None]], 
                                 columns=['Data Hora', 'Ax1', 'Ay1', 'Az1', 'Oscilação1', 'Frequência1',
                                          'Ax2', 'Ay2', 'Az2', 'Oscilação2', 'Frequência2',
                                          'Q0_1', 'Q1_1', 'Q2_1', 'Q3_1', 
                                          'Q0_2', 'Q1_2', 'Q2_2', 'Q3_2'])
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self.df.to_excel(f"{self.file_name}.xlsx", index=False)


    def end_test(self):
        self.running = False
        result = messagebox.askyesno("Teste Concluído", "O teste foi concluído. Deseja reiniciar o teste?")
        if result:
            self.restart_test()
        else:
            self.master.quit()


    def restart_test(self):
        self.running = False  # Para evitar travamento
        self.data1 = []
        self.data2 = []
        self.oscillation_data = []
        self.frequency1 = 0
        self.frequency2 = 0
        self.start_time = time.time()
        self.last_export_time = time.time()
        self.file_name = self.ask_file_name()
        self.create_excel_file()
        self.running = True
        self.update_data()  # Inicia novamente a atualização


if __name__ == "__main__":
    root = tk.Tk()
    login_app = LoginApp(root)
    root.mainloop()
