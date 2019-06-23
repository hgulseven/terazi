import tkinter as tk
from tkinter import Button
from tkinter.ttk import Combobox
from typing import Any, Tuple
import pyodbc
import time
import threading
from tkinter import *
import serial


class Product(object):
    def __init__(self, productName=None, price=None, teraziID=None):
        self.productName = productName
        self.price = price
        self.teraziID = teraziID


class Reyon:
    def __init__(self, teraziID=None, ReyonName=None):
        self.teraziID = teraziID
        self.ReyonName = ReyonName


class Employee:
    def __init__(self,personelID=None, Persname=None):
        self.personelID = personelID
        self.Persname = Persname


product_names = []
reyons = []
employees = []


def load_products(self, ID):
    str = 'DRIVER={Easysoft ODBC-SQL Server};SERVER=192.168.1.101\\SQLEXPRESS;USER=hakan;PASSWORD=ZXCvbn123;DATABASE=GULSEVEN;'
    str = 'DSN=GULSEVEN;UID=hakan;PWD=ZXCvbn123'

    conn = pyodbc.connect(str)
    cursor = conn.cursor()
    cursor.execute("Select  TeraziID,productName, productRetailPrice from [dbo].[ProductModels]"
                   " left outer join [dbo].[TeraziScreenMapping] on "
                   "([dbo].[TeraziScreenMapping].productID=[dbo].[ProductModels].productID)"
                   "where TeraziID=?", ID)
    product_names.clear()
    for row in cursor:
        productObj = Product()
        productObj.teraziID = row[0]
        productObj.productName = row[1]
        productObj.price = row[2]
        product_names.append(productObj)
    cursor.close()


class loadTables:

    def __init__(self):
        load_products(self, 1)
        str = 'DRIVER={Easysoft ODBC-SQL Server};SERVER=192.168.1.101\\SQLEXPRESS;USER=hakan;PASSWORD=ZXCvbn123;LANGUAGE=Turkish;DATABASE=GULSEVEN;'
        str = 'DSN=GULSEVEN;UID=hakan;PWD=ZXCvbn123'
        conn = pyodbc.connect(str)
        cursor = conn.cursor()
        cursor.execute("Select  TeraziID, teraziName from [dbo].[TeraziTable]")
        for row in cursor:
            reyonObj = Reyon()
            reyonObj.teraziID = row[0]
            reyonObj.ReyonName = row[1]
            reyons.append(reyonObj)

        cursor.execute("Select personelID, persName,persSurname  from  [dbo].[EmployeesModels]")
        for row in cursor:
            employeeObj = Employee()
            employeeObj.Persname = row[1] + " " + row[2]
            employeeObj.personelID = row[0]
            employees.append(employeeObj)



class MainWindow(tk.Tk):

    def __init__(self):

        tk.Tk.__init__(self)
        serial_data = ''
        filter_data = ''
        update_period = 60
        serial_object = None
        self.geometry('800x480')
        loadTables()
        self.display_frame = tk.Frame(self)
        self.scale_display = tk.Text(self.display_frame, height=1, width=14, font=("Arial Bold", 25),
                                     bg='dark green', fg="white")
        self.scale_type = tk.Text(self.display_frame, height=1, width=3, font=("Arial Bold", 25),
                                  bg='dark green', fg="white")
        self.scale_type.insert(END, "Kg")
        self.employee_frame = tk.Frame(self)
        self.product_frame = tk.Frame(self)
        self.functions_frame = tk.Frame(self)
        self.employee_frame_def()
        new_data = threading.Event()
        t2 = threading.Thread(target=update_gui, args=(self.scale_display, new_data,))
        t2.daemon = True
        t2.start()
        connect(new_data, 9600, 'USB0')

    def employee_frame_def(self):
        row_size, col_size = 4, 2
        for btn_no, employee in enumerate(employees):
            button = Button(self.employee_frame, text=employee.Persname)
            button.configure(command=lambda btn=button: self.employee_button_clicked(btn))
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)

        self.employee_frame.pack()

    def product_frame_def(self):
        reyon_names = []
        for index, reyonObj in enumerate(reyons):
            reyon_names.append(reyonObj.ReyonName)
        self.select_reyon = Combobox(self.display_frame, font=("Arial Bold", 25), values=reyon_names)
        self.select_reyon.bind("<<ComboboxSelected>>", self.checkreyon)
        self.select_reyon
        self.select_reyon.grid(row=0, column=0)
        self.scale_display.grid(row=0, column=1)
        self.scale_type.grid(row=0, column=2)
        self.display_frame.pack()
        row_size, col_size = 8, 4
        for btn_no, Product in enumerate(product_names):
            button = Button(self.product_frame, font=("Arial Bold", 12), wraplength=150, text=Product.productName, width=15, height=3)
            button.configure(command=lambda btn=button: self.product_button_clicked(btn))
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)
        self.product_frame.pack()
        self.functions_frame.pack_forget()
        self.functions_frame = tk.Frame(self)
        self.functions_frame.pack()
        button = Button(self.functions_frame, font=("Arial Bold", 12), wraplength=150, text="Dara", width=20,
                        height=3)
        button.configure(command=lambda btn=button: self.product_button_clicked(btn))
        button.pack()


    def checkreyon(self, event: object):
        tt = self.select_reyon.get()
        kk = self.select_reyon.current()
        teraziID = [x.teraziID for x in reyons if x.ReyonName == tt]
        load_products(self, teraziID[0])
        self.select_reyon.pack_forget()
        self.product_frame.pack_forget()
        self.display_frame.pack_forget()
        self.product_frame_def()
        self.select_reyon.current(kk)

    def employee_button_clicked(self, btn):
        my_text = btn.cget("text")
        self.employee_frame.pack_forget()
        self.product_frame_def()

    def product_button_clicked(self, btn):
        my_text = btn.cget("text")



def connect(new_data, baud, port):
    """The function initiates the Connection to the UART device with the Port and Buad fed through the Entry
    boxes in the application.

    The radio button selects the platform, as the serial object has different key phrases
    for Linux and Windows. Some Exceptions have been made to prevent the app from crashing,
    such as blank entry fields and value errors, this is due to the state-less-ness of the
    UART device, the device sends data at regular intervals irrespective of the master's state.

    The other Parts are self explanatory.
    """

    version_ = 2
    global serial_object

    try:
        if version_ == 2:
            try:
                serial_object = serial.Serial('/dev/tty' + str(port), baud)

            except:
                print("Cant Open Specified Port")
        elif version_ == 1:
            serial_object = serial.Serial('COM' + str(port), baud)

    except ValueError:
        print("Enter Baud and Port")
        return

    t1 = threading.Thread(target=get_data,
                          args=(new_data,))
    t1.daemon = True
    t1.start()


def get_data(new_data):
    """This function serves the purpose of collecting data from the serial object and storing
    the filtered data into a global variable.

    The function has been put into a thread since the serial event is a blocking function.
    """
    global serial_object
    global filter_data
    filter_data = ""
    while (1):
        try:
            serial_data = str(serial_object.readline(), 'utf-8')
            serial_data = serial_data.rstrip('\r')
            serial_data = serial_data.rstrip('\n')
            if (serial_data[0:1] == '+') and (filter_data != serial_data[4:serial_data.index("kg")]):
                filter_data = serial_data[4:serial_data.index("kg")]
                new_data.set()
                print(filter_data)
            else:
                pass

        except TypeError:
            pass
        except UnicodeDecodeError:
            pass


def update_gui(scale_display, new_data):
    """" This function is an update function which is also threaded. The function assimilates the data
    and applies it to it corresponding progress bar. The text box is also updated every couple of seconds.

    A simple auto refresh function .after() could have been used, this has been avoid purposely due to
    various performance issues.


    """
    global filter_data

    while (1):
        event_is_set = new_data.wait()
        new_data.clear()
        if filter_data:
            scale_display.delete(1.0, END)
            mydata = filter_data
            mydata = mydata.rjust(25)
            scale_display.insert(END, mydata)


MainWindow().mainloop()
