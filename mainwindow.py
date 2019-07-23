import tkinter as tk
from tkinter import *
from tkinter.ttk import *
import pyodbc
import threading
import serial
import datetime
import time
import requests

glb_cursor = 0  # global cursor for db access. Initialized in load_products
glb_customer_no = 0  # customer no is got by using salesCounter table.
top = None
glb_product_names = []  # products are loaded to memory based on rayon
glb_reyons = []  # rayon combobox contents
glb_employees = []  # employees loaded to this global collection
glb_sales = []  # sales for the active customer loaded to this collection
glb_active_served_customers = []  # active customers loaded to this collection
glb_customers_on_cashier = []  # customers that were sent to cashier. Actively waiting for payment
# product frame is used for various selections such as Products, Customers
# employees, customer callback if the value is
# 0: employees
# 1: products
# 2: Customers
# 3:Call back customers
# this variable is used for next, previous buttons and set when page display content is changed
glb_active_product_frame_content = 0  # shows contents of product frame which is used more than one purpose
glb_connection_str = 'DSN=GULSEVEN;UID=sa;PWD=QAZwsx135'
# glb_connection_str = 'DRIVER={FreeTDS};SERVER=192.168.1.106;PORT=51012;DATABASE=GULSEVEN;UID=hakan;PWD=ZXCvbn123;TDS_Version=7.2'
glb_scaleId = 0
glb_employeeselected = ''  # name of the selected employee.
glb_sales_line_id = 1    # line of the sales
glb_base_weight = 0      # tare weight is stored in this variable. Updated when tare button is clicked.
glb_product_page_count = 0    # paging of product buttons displayed in product frame
glb_employees_page_count = 0  # paging of employee buttons displayed in product frame
glb_active_customers_page_count = 0  # paging of active customers buttons displayed in product frame
glb_callback_customers_page_count = 0  # paging of callback customers buttons displayed in product frame

class Product(object):
    def __init__(self, productID=None, Name=None, price=None, teraziID=None):
        self.productID = productID
        self.Name = Name
        self.price = price
        self.teraziID = teraziID


class Customer(object):
    def __init__(self, customer_no=None):
        self.Name = customer_no


class Reyon(object):
    def __init__(self, teraziID=None, ReyonName=None):
        self.teraziID = teraziID
        self.ReyonName = ReyonName


class Employee(object):
    def __init__(self, personelID=None, Name=None):
        self.personelID = personelID
        self.Name = Name


class SalesCounter(object):
    def __init__(self, salesDate=None, counter=None):
        self.salesDate = salesDate
        self.counter = 0

    def getcounter(self):
        global glb_cursor
        # conn = pyodbc.connect(glb_connection_str)
        # cursor = conn.cursor()
        mydate = datetime.date.today()
        glb_cursor.execute("select counter from salesCounter where salesDate=?", mydate.strftime('%Y-%m-%d'))
        number_of_rows = 0
        for row in glb_cursor:
            number_of_rows = number_of_rows + 1
            self.counter = row[0] + 1
        if number_of_rows > 0:
            glb_cursor.execute("Update salesCounter set counter=? where salesDate=?", self.counter,
                           mydate.strftime('%Y-%m-%d'))
        else:
            self.counter = 1
            glb_cursor.execute("Insert into salesCounter (salesDate, counter) values (?,?)", mydate.strftime('%Y-%m-%d'),
                           self.counter)
        glb_cursor.commit()
        # cursor.close()
        return self.counter


class Sales(object):
    def __init__(self, salesID=None, salesLineID=None, personelID=None, productID=None, Name=None,
                 retailPrice=None, amount=None, typeOfCollection=None):
        mydate = datetime.date.today()
        self.saleDate = mydate.strftime('%Y-%m-%d')
        self.salesID = salesID
        self.salesLineID = salesLineID
        self.personelID = personelID
        self.productID = productID
        self.Name = Name
        self.retailPrice = retailPrice
        self.amount = amount
        self.typeOfCollection = typeOfCollection
        # -1 active customer still being served;
        # -2 customer sales canceled;
        # 0 send to cashier waiting for payment;
        # 1 paid in cash;
        # 2 paid by credit card;
        # 3 other type of payment;


def sales_update(salesID, srcTypeOfCollection, destTypeOfCollection):
    global glb_cursor
    # conn = pyodbc.connect(glb_connection_str)
    # cursor = conn.cursor()
    for salesObj in glb_sales:
        glb_cursor.execute(
            "update dbo.SalesModels set saleDate=?, salesID=?,  salesLineID=?, personelID=?, productID=?, amount=?, typeOfCollection=? "
            "where salesID=? and salesLineID=? and typeOfCollection=? and saleDate=?"
            , salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID, salesObj.productID,
            salesObj.amount, destTypeOfCollection, salesID, salesObj.salesLineID, srcTypeOfCollection,
            salesObj.saleDate)
    glb_cursor.commit()
    # cursor.close()


def sales_save(typeOfCollection):
    global glb_cursor
    # conn = pyodbc.connect(glb_connection_str)
    # cursor = conn.cursor()
    for salesObj in glb_sales:
        glb_cursor.execute(
            "select count(*) from dbo.SalesModels where salesID=? and typeOfCollection=? and salesLineID=? and saleDate=?",
            salesObj.salesID, -1, salesObj.salesLineID, salesObj.saleDate)
        number_of_rows = glb_cursor.fetchone()[0]
        if number_of_rows > 0:
            glb_cursor.execute(
                "update dbo.SalesModels set saleDate=?, salesID=?,  salesLineID=?, personelID=?, productID=?, amount=?,"
                "typeOfCollection=? where personelID=? and typeOfCollection=? and salesID=? and salesLineID=? and saleDate=?"
                , salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID, salesObj.productID,
                salesObj.amount, typeOfCollection, salesObj.personelID, typeOfCollection, salesObj.salesID, salesObj.salesLineID,
                salesObj.saleDate)
        else:
            glb_cursor.execute(
                "insert into dbo.SalesModels (saleDate, salesID,  salesLineID, personelID, productID, amount, typeOfCollection) values (?,?,?,?,?,?,?)"
                , salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID, salesObj.productID,
                salesObj.amount, typeOfCollection)
    glb_cursor.commit()
    # cursor.close()


def sales_load(salesID, typeOfCollection):
    global glb_customer_no
    global glb_sales_line_id
    global glb_customer_no
    global glb_cursor
    # conn = pyodbc.connect(glb_connection_str)
    # cursor = conn.cursor()
    glb_cursor.execute(
        "select  saleDate, salesID,  salesLineID, personelID, SalesModels.productID, amount, productRetailPrice, "
        "productName, typeOfCollection from dbo.SalesModels "
        "left outer join ProductModels "
        "on (SalesModels.productID= ProductModels.productID) "
        "where salesId=? and typeOfCollection=?",
        salesID, typeOfCollection)
    glb_sales_line_id = 1
    for row in glb_cursor:
        glb_customer_no = row[1]
        salesObj = Sales()
        salesObj.saleDate = row[0]
        salesObj.salesID = row[1]
        salesObj.salesLineID = row[2]
        salesObj.personelID = row[3]
        salesObj.productID = row[4]
        salesObj.amount = row[5]
        salesObj.retailPrice = row[6]
        salesObj.Name = row[7]
        salesObj.typeOfCollection = row[8]
        glb_sales.append(salesObj)
        glb_sales_line_id = glb_sales_line_id + 1
    # cursor.close


def get_product_based_on_barcod(prdct_barcode, salesObj):
    global glb_cursor
    global glb_sales_line_id
    global glb_customer_no
    global glb_employeeselected
    glb_cursor.execute(
        "Select productID, Name, productRetailPrice from [dbo].[ProductModels]"
        "where productBarcodeID=?", prdct_barcode)
    for row in glb_cursor:
        salesObj.salesID = glb_customer_no
        salesObj.salesLineID = glb_sales_line_id
        glb_sales_line_id = glb_sales_line_id+1
        salesObj.personelID = [x.personelID for x in glb_employees if x.Name == glb_employeeselected][0]
        salesObj.productID = row[0]
        salesObj.amount = 1
        salesObj.Name = row[1]
        salesObj.retailPrice = row[2]
        salesObj.typeOfCollection = 0


def get_served_customers():
    global glb_active_served_customers
    global glb_cursor
    # db_connected = FALSE
    # while not db_connected:
    #    try:
    #        conn = pyodbc.connect(glb_connection_str)
    #        db_connected = TRUE
    #    except:
    #        db_connected = FALSE
    #        time.sleep(2)
    # cursor = conn.cursor()
    glb_cursor.execute(
        "Select  distinct salesID from [dbo].[SalesModels]"
        "where  typeOfCollection = -1 order by salesID")
    for row in glb_cursor:
        customer_obj = Customer()
        customer_obj.Name = row[0]
        glb_active_served_customers.append(customer_obj)
    # cursor.close()


def get_customers_on_cashier():
    global glb_customers_on_cashier
    global glb_cursor
    # db_connected = FALSE
    # while not db_connected:
    #    try:
    #        conn = pyodbc.connect(glb_connection_str)
    #        db_connected = TRUE
    #    except:
    #        db_connected = FALSE
    #        time.sleep(2)
    # cursor = conn.cursor()
    glb_customers_on_cashier.clear()
    glb_cursor.execute(
        "Select  distinct salesID from [dbo].[SalesModels]"
        "where  typeOfCollection = 0 order by salesID")
    for row in glb_cursor:
        customer_obj = Customer()
        customer_obj.Name = row[0]
        glb_customers_on_cashier.append(customer_obj)
    # cursor.close()


def load_products(self, ID):
    global glb_cursor
    db_connected = FALSE
    while not db_connected:
        try:
            conn = pyodbc.connect(glb_connection_str)
            db_connected = TRUE
        except:
            db_connected = FALSE
            time.sleep(2)
    glb_cursor = conn.cursor()
    glb_cursor.execute(
        "Select  TeraziID, [dbo].[ProductModels].productID, productName, productRetailPrice from [dbo].[ProductModels]"
        " left outer join [dbo].[TeraziScreenMapping] on "
        "([dbo].[TeraziScreenMapping].productID=[dbo].[ProductModels].productID)"
        "where TeraziID=? order by screenSeqNo", ID)
    glb_product_names.clear()
    for row in glb_cursor:
        productObj = Product()
        productObj.teraziID = row[0]
        productObj.productID = row[1]
        productObj.Name = row[2]
        productObj.price = float(row[3])
        glb_product_names.append(productObj)
    # cursor.close()


class loadTables:

    def __init__(self):
        global glb_scaleId
        global glb_sales_line_id
        global glb_base_weight
        global glb_customer_no
        global glb_cursor

        load_products(self, 1)
        glb_scaleId = 0
        glb_sales_line_id = 1
        glb_base_weight = 0
        glb_customer_no = 0
        # conn = pyodbc.connect(glb_connection_str)
        # cursor = conn.cursor()
        glb_cursor.execute("Select  TeraziID, teraziName from [dbo].[TeraziTable]")
        for row in glb_cursor:
            reyonObj = Reyon()
            reyonObj.teraziID = row[0]
            reyonObj.ReyonName = row[1]
            glb_reyons.append(reyonObj)
        glb_cursor.execute("Select personelID, persName,persSurname  from  [dbo].[employeesModels]")
        for row in glb_cursor:
            employeeObj = Employee()
            employeeObj.Name = row[1] + " " + row[2]
            employeeObj.personelID = row[0]
            glb_employees.append(employeeObj)


def maininit(top, gui, *args, **kwargs):
    global w, top_level, root
    w = gui
    top_level = top
    root = top


def vp_start_gui():
    '''Starting point when module is the main routine.'''
    global w, root, top
    root = tk.Tk()
    top = MainWindow(root)
    maininit(root, top)
    root.mainloop()


class MainWindow(tk.Tk):

    def message_box_frame_def(self):
        global top
        self.message_box_frame.place(relx=0.0, rely=0.900, relheight=0.10, relwidth=0.994)
        self.message_box_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9")
        self.message_box_frame.configure(highlightbackground="#f0f0f0", width=795)
        self.message_box_text = tk.Text(self.message_box_frame, height=1, width=80, font=("Arial Bold", 12),
                                        bg='dark red', fg="white")
        self.message_box_text.place(relx=0.0, rely=0.0, relheight=0.60, relwidth=0.994)

    def paging_frame_def(self):
        global top
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        self.paging_frame.place(relx=0.28, rely=0.560, relheight=0.120, relwidth=0.700)
        self.paging_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        next_button = tk.Button(self.paging_frame, text="Sonraki Sayfa")
        next_button.configure(activebackground="#ececec", activeforeground="#000000", background="dark red")
        next_button.configure(disabledforeground="#a3a3a3", font=font11, foreground="white")
        next_button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=2,
                              wraplength=130)
        next_button.configure(command=lambda btn=next_button: self.next_product_button_clicked())
        next_button.grid(row=0, column=2)
        previous_button = tk.Button(self.paging_frame, text="Önceki Sayfa")
        previous_button.configure(activebackground="#ececec", activeforeground="#000000", background="dark red")
        previous_button.configure(disabledforeground="#a3a3a3", font=font11, foreground="white")
        previous_button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=2,
                                  wraplength=130)
        previous_button.configure(command=lambda btn=previous_button: self.previous_product_button_clicked())
        previous_button.grid(row=0, column=0)

    def employee_frame_def(self):
        global top
        global glb_active_product_frame_content
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        glb_active_product_frame_content = 0
        for child in self.product_frame.winfo_children():
            child.destroy()
        self.product_frame.place(relx=0.28, rely=0.110, relheight=0.440, relwidth=0.700)
        self.product_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        row_size, col_size = 4, 3
        for btn_no, employee in enumerate(glb_employees):
            button = tk.Button(self.product_frame, text=employee.Name)
            button.configure(command=lambda btn=button: self.employee_button_clicked(btn))
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9",
                             disabledforeground="#a3a3a3")
            button.configure(font=font11, foreground="#000000", highlightbackground="#d9d9d9", highlightcolor="black",
                             pady="0", width=13, height=2)
            button.configure(wraplength=130)
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)

    def customer_frame_def(self):
        global glb_active_served_customers
        global top
        global glb_active_product_frame_content
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        glb_active_product_frame_content = 2
        glb_active_served_customers.clear()
        for child in self.product_frame.winfo_children():
            child.destroy()
        self.product_frame.place(relx=0.28, rely=0.110, relheight=0.440, relwidth=0.700)
        self.product_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        row_size, col_size = 4, 3
        get_served_customers()
        btn_no = 0
        for btn_no, customer_obj in enumerate(glb_active_served_customers):
            button = tk.Button(self.product_frame, text=customer_obj.Name)
        for btn_no, customer_obj in enumerate(glb_active_served_customers):
            button = tk.Button(self.product_frame, text=customer_obj.customerNo)
            button.configure(command=lambda btn=button: self.customer_button_clicked(btn))
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9",
                             disabledforeground="#a3a3a3")
            button.configure(font=font11, foreground="#000000", highlightbackground="#d9d9d9", highlightcolor="black",
                             pady="0", width=13, height=2)
            button.configure(wraplength=130)
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)
        btn_no = btn_no + 1
        button = tk.Button(self.product_frame, text="Yeni Müşteri")
        button.configure(command=lambda btn=button: self.new_customer_clicked())
        button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9",
                         disabledforeground="#a3a3a3")
        button.configure(font=font11, foreground="#000000", highlightbackground="#d9d9d9", highlightcolor="black",
                         pady="0", width=13, height=2)
        button.configure(wraplength=130)
        button.grid(row=int(btn_no / col_size), column=btn_no % col_size)

    def call_back_customer_frame_def(self):
        global glb_customers_on_cashier
        global top
        global glb_active_product_frame_content
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        glb_active_product_frame_content = 3
        glb_customers_on_cashier.clear()
        for child in self.product_frame.winfo_children():
            child.destroy()
        self.product_frame.place(relx=0.28, rely=0.110, relheight=0.440, relwidth=0.700)
        self.product_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        row_size, col_size = 4, 3
        get_customers_on_cashier()
        btn_no = 0
        for btn_no, customer_obj in enumerate(glb_customers_on_cashier):
            button = tk.Button(self.product_frame, text=customer_obj.Name)
            button.configure(command=lambda btn=button: self.call_back_customer_no_clicked(btn))
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9",
                             disabledforeground="#a3a3a3")
            button.configure(font=font11, foreground="#000000", highlightbackground="#d9d9d9", highlightcolor="black",
                             pady="0", width=13, height=2)
            button.configure(wraplength=130)
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)


    def call_back_customer_frame_def(self):
        global glb_customers_on_cashier
        global top
        global glb_active_product_frame_content
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        glb_active_product_frame_content = 3
        glb_customers_on_cashier.clear()
        for child in self.product_frame.winfo_children():
            child.destroy()
        self.product_frame.place(relx=0.28, rely=0.110, relheight=0.440, relwidth=0.700)
        self.product_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        row_size, col_size = 4, 3
        get_customers_on_cashier()
        btn_no = 0
        for btn_no, customer_obj in enumerate(glb_customers_on_cashier):
            button = tk.Button(self.product_frame, text=customer_obj.customerNo)
            button.configure(command=lambda btn=button: self.call_back_customer_no_clicked(btn))
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9",
                             disabledforeground="#a3a3a3")
            button.configure(font=font11, foreground="#000000", highlightbackground="#d9d9d9", highlightcolor="black",
                             pady="0", width=13, height=2)
            button.configure(wraplength=130)
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)


    def display_frame_def(self):
        global top

        self.display_frame.place(relx=0.0, rely=0.0, relheight=0.100, relwidth=0.994)
        self.product_frame.configure(width=795)
        self.customer_no = tk.Text(self.display_frame, height=1, width=4, font=("Arial Bold", 25),
                                   bg='dark blue', fg="white")
        self.scale_display = tk.Text(self.display_frame, height=1, width=12, font=("Arial Bold", 25),
                                     bg='dark green', fg="white")
        self.scale_type = tk.Text(self.display_frame, height=1, width=3, font=("Arial Bold", 25),
                                  bg='dark green', fg="white")
        self.prdct_barcode = tk.Text(self.display_frame, height=1, width=5, font=('Arial Bold', 25))
        self.scale_type.insert(END, "Kg")
        self.customer_no.insert(END, "0")
        reyon_names = []
        for index, reyonObj in enumerate(glb_reyons):
            reyon_names.append(reyonObj.ReyonName)
        self.select_reyon = Combobox(self.display_frame, font=("Arial Bold", 22), values=reyon_names)
        self.select_reyon.bind("<<ComboboxSelected>>", self.checkreyon)
        self.select_reyon
        self.prdct_barcode.grid(row=0, column=0)
        self.select_reyon.grid(row=0, column=1)
        self.customer_no.grid(row=0, column=2)
        self.scale_display.grid(row=0, column=3)
        self.scale_type.grid(row=0, column=4)
        self.prdct_barcode.focus_set()
        self.prdct_barcode.bind('<Key-Return>', self.read_barcode)

    def read_barcode(self, event):
        global glb_sales
        textdata = self.prdct_barcode.get('1.0', END)
        textdata = textdata.rstrip("\n")
        textdata = textdata.lstrip("\n")
        self.prdct_barcode.delete('1.0', END)
        salesObj = Sales()
        get_product_based_on_barcod(textdata, salesObj)
        glb_sales.append(salesObj)
        self.update_products_sold()

    def add_product_buttons(self):
        global glb_product_page_count
        font11 = "-family {Segoe UI} -size 11 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        for child in self.product_frame.winfo_children():
            child.destroy()
        row_size, col_size = 4, 3
        lower_product_cnt = glb_product_page_count * row_size * col_size
        while lower_product_cnt > len(glb_product_names):
            glb_product_page_count = glb_product_page_count - 1
            lower_product_cnt = glb_product_page_count * row_size * col_size
        upper_product_cnt = lower_product_cnt + 12
        if upper_product_cnt > len(glb_product_names):
            upper_product_cnt = len(glb_product_names)
        btn_no = 0
        while lower_product_cnt < upper_product_cnt:
            prod = glb_product_names[lower_product_cnt]
            button = tk.Button(self.product_frame, text=prod.Name)
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
            button.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
            button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=2,
                             wraplength=130)
            button.configure(command=lambda btn=button: self.product_button_clicked(btn))
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)
            btn_no = btn_no + 1
            lower_product_cnt = lower_product_cnt + 1

    def add_frame_buttons(self, frame, list, page_count, func):
        font11 = "-family {Segoe UI} -size 11 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        for child in frame.winfo_children():  # Clear frame contents whatever it is
            child.destroy()
        row_size, col_size = 4, 3   # grid in the frame is 4 by 3
        lower_cnt = page_count * row_size * col_size    # calculate lower bound in the list
        while lower_cnt > len(list):    # if lower bound is more than list size adjust it
            page_count = page_count - 1
            lower_cnt = page_count * row_size * col_size
        upper_cnt = lower_cnt + row_size * col_size  # calculate upper bound in the list
        if upper_cnt > len(list):   # if upper bound more than list size adjust it
            upper_cnt = len(list)
        btn_no = 0
        while lower_cnt < upper_cnt:
            obj = list[lower_cnt]
            button = tk.Button(frame, text=obj.Name)
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
            button.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
            button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=2,
                             wraplength=130)
            button.configure(command=lambda btn=button: func(btn))
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)
            btn_no = btn_no + 1
            lower_cnt = lower_cnt + 1


    def product_frame_def(self):
        global top
        global glb_active_product_frame_content
        self.product_frame.place(relx=0.28, rely=0.110, relheight=0.440, relwidth=0.700)
        self.product_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        glb_active_product_frame_content = 1
        varfunc = self.product_button_clicked
        self.add_frame_buttons(self.product_frame, glb_product_names, glb_product_page_count, varfunc)

    def productssold_frame_def(self):
        global top
        font11 = "-family {Segoe UI} -size 8 -slant " \
                 "roman -underline 0 -overstrike 0"
        font9 = "-family {Segoe UI} -size 11 -weight bold -slant roman" \
                " -underline 0 -overstrike 0"
        self.products_sold_frame.place(relx=0.0, rely=0.110, relheight=0.550, relwidth=0.280)
        self.products_sold_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9",
                                           highlightbackground="#d9d9d9")
        self.products_sold_frame.configure(highlightcolor="black", width=155)
        self.entry_products = tk.Text(self.products_sold_frame)
        self.entry_products.place(relx=0.010, rely=0.02, relheight=0.84, relwidth=0.700)
        self.entry_products.configure(font=font11)
        self.entry_products.configure(takefocus="")
        self.entry_calculatedtotal = tk.Text(self.products_sold_frame)
        self.entry_calculatedtotal.place(relx=0.720, rely=0.02, relheight=0.84, relwidth=0.240)
        self.entry_calculatedtotal.configure(font=font11, takefocus="")
        self.label_sum = tk.Label(self.products_sold_frame)
        self.label_sum.place(relx=0.040, rely=0.88, relheight=0.10, relwidth=0.300)
        self.label_sum.configure(background="#d9d9d9")
        self.label_sum.configure(disabledforeground="#a3a3a3")
        self.label_sum.configure(font=font9)
        self.label_sum.configure(foreground="#000000")
        self.label_sum.configure(text='''Toplam''')
        self.entry_sum = tk.Text(self.products_sold_frame, height=1, width=80, font=("Arial Bold", 12))
        self.entry_sum.place(relx=0.650, rely=0.88, relheight=0.10, relwidth=0.350)

    def functions_frame_def(self):
        global top
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"

        self.functions_frame.place(relx=0.0, rely=0.700, relheight=0.200, relwidth=0.994)
        self.functions_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9")
        self.functions_frame.configure(highlightbackground="#f0f0f0", width=795)

        self.btn_dara = tk.Button(self.functions_frame)
        self.btn_dara.configure(command=lambda btn=self.btn_dara: self.btn_dara_clicked())
        self.btn_dara.place(relx=0.013, rely=0.050, height=35, width=160)
        self.btn_dara.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_dara.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_dara.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", text='''Dara''',
                                width=15)

        self.btn_changeuser = tk.Button(self.functions_frame)
        self.btn_changeuser.configure(command=lambda btn=self.btn_changeuser: self.btn_change_user_clicked())
        self.btn_changeuser.place(relx=0.264, rely=0.050, height=35, width=160)
        self.btn_changeuser.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_changeuser.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_changeuser.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                      text='''Çalışan Değiştir''', width=15)

        self.btn_call_back_customer = tk.Button(self.functions_frame)
        self.btn_call_back_customer.configure(
            command=lambda btn=self.btn_call_back_customer: self.call_back_customer_clicked())
        self.btn_call_back_customer.place(relx=0.516, rely=0.050, height=35, width=160)
        self.btn_call_back_customer.configure(activebackground="#ececec", activeforeground="#000000",
                                              background="#d9d9d9")
        self.btn_call_back_customer.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_call_back_customer.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                              text='''Müşteri Geri Çağır''', width=15)

        self.btn_cancelsale = tk.Button(self.functions_frame)
        self.btn_cancelsale.configure(command=lambda btn=self.btn_cancelsale: self.btn_cancelsale_clicked())
        self.btn_cancelsale.place(relx=0.767, rely=0.050, height=35, width=160)
        self.btn_cancelsale.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_cancelsale.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_cancelsale.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                      text='''Satışı İptal Et''', width=15)

        self.btn_cleardara = tk.Button(self.functions_frame)
        self.btn_cleardara.configure(command=lambda btn=self.btn_cleardara: self.btn_cleardara_clicked())
        self.btn_cleardara.place(relx=0.013, rely=0.500, height=35, width=160)
        self.btn_cleardara.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_cleardara.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000",
                                     text='''Darayı Temizle''', width=15)

        self.btn_savesale = tk.Button(self.functions_frame)
        self.btn_savesale.configure(command=lambda btn=self.btn_savesale: self.btn_savesale_clicked())
        self.btn_savesale.place(relx=0.264, rely=0.500, height=35, width=160)
        self.btn_savesale.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_savesale.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000",
                                    text='''Satışı Kaydet''', width=15)

        self.btn_sendcashier = tk.Button(self.functions_frame)
        self.btn_sendcashier.configure(command=lambda btn=self.btn_sendcashier: self.btn_sendcashier_clicked())
        self.btn_sendcashier.place(relx=0.516, rely=0.500, height=35, width=160)
        self.btn_sendcashier.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_sendcashier.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_sendcashier.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                       text='''Kasaya Gönder''', width=15)

        self.btn_clearlasttransaction = tk.Button(self.functions_frame)
        self.btn_clearlasttransaction.configure(
            command=lambda btn=self.btn_clearlasttransaction: self.btn_clearlasttransaction_clicked())
        self.btn_clearlasttransaction.place(relx=0.767, rely=0.500, height=35, width=160)
        self.btn_clearlasttransaction.configure(activebackground="#ececec", activeforeground="#000000",
                                                background="#d9d9d9")
        self.btn_clearlasttransaction.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_clearlasttransaction.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                                text='''Son İşlemi Sil''', width=15)

    def next_product_button_clicked(self):
        global glb_product_page_count
        global glb_callback_customers_page_count
        global glb_active_customers_page_count
        global glb_employees_page_count
        global glb_active_product_frame_content

        if glb_active_product_frame_content == 0:  # Middle frame is used for employees
            glb_employees_page_count = glb_employees_page_count + 1
        elif glb_active_product_frame_content == 1:  # Middle frame is used for products
            glb_product_page_count = glb_product_page_count + 1
            self.add_product_buttons()
        elif glb_active_product_frame_content == 2:  # Middle frame is used for customers
            glb_active_customers_page_count = glb_active_customers_page_count + 1
        else:  # Middle frame for callback customers
            glb_callback_customers_page_count = glb_callback_customers_page_count + 1

    def previous_product_button_clicked(self):
        global glb_product_page_count
        global glb_active_product_frame_content

        if glb_active_product_frame_content == 0:  # Middle frame is used for employees
            ss = 1
        elif glb_active_product_frame_content == 1:  # Middle frame is used for products
            if glb_product_page_count > 0:
                glb_product_page_count = glb_product_page_count - 1
            self.add_product_buttons()
        elif glb_active_product_frame_content == 2:  # Middle frame is used for customers
            ss = 2
        else:  # Middle frame for callback customers
            ss = 3

    def customer_button_clicked(self, btn):
        global glb_customer_no

        glb_customer_no = btn.cget("text")
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        sales_load(glb_customer_no, -1)
        self.product_frame_def()
        self.update_products_sold()

    def btn_sendcashier_clicked(self):
        global glb_customer_no
        global glb_sales_line_id

        sales_save(-1)
        sales_update(glb_customer_no, -1, 0)  #  update which has value -1 (actively served customer) to 0 (sent to cashier)
        glb_sales.clear()
        self.update_products_sold()
        glb_customer_no = 0
        glb_sales_line_id = 1
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, "0")
        resp = requests.get("http://gulsevensrv/api/DataRefresh")
        self.new_customer_clicked()

    def btn_change_user_clicked(self):
        global top
        global glb_employeeselected
        global glb_customer_no

        glb_sales.clear()
        glb_customer_no = 0
        self.update_products_sold()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        self.employee_frame_def()
        glb_employeeselected = ""

    def call_back_customer_no_clicked(self, btn):
        salesID=btn.cget("text")
        glb_sales.clear()
        sales_load(salesID, 0)
        sales_update(salesID, 0, -1)
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        self.update_products_sold()
        self.product_frame_def()

    def call_back_customer_no_clicked(self, btn):
        salesID=btn.cget("text")
        glb_sales.clear()
        sales_load(salesID, 0)
        sales_update(salesID, 0, -1)
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        self.update_products_sold()
        self.product_frame_def()
        resp = requests.get("http://gulsevensrv/api/DataRefresh")


    def call_back_customer_clicked(self):
        self.call_back_customer_frame_def()

    def new_customer_clicked(self):
        global top
        global glb_sales_line_id
        global glb_employeeselected
        global glb_customer_no

        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        salescounterobj = SalesCounter()
        glb_customer_no = salescounterobj.getcounter()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        glb_sales_line_id = 1
        self.product_frame_def()

    def btn_cancelsale_clicked(self):

        global top
        global glb_sales_line_id
        global glb_employeeselected
        global glb_customer_no

        sales_save(-2)
        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        self.update_products_sold()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, "0")
        glb_sales_line_id = 1
        glb_customer_no = 0
        self.new_customer_clicked()

    def btn_savesale_clicked(self):
        global glb_sales_line_id

        sales_save(-1)
        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        self.update_products_sold()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, "0")
        glb_sales_line_id = 1
        self.btn_change_user_clicked()

    def btn_dara_clicked(self):
        global glb_base_weight
        glb_base_weight = float(self.scale_display.get("1.0", END).strip("\n"))
        self.scale_display.delete("1.0", END)
        self.scale_display.insert(END, "0.000".rjust(20))

    def btn_cleardara_clicked(self):
        global glb_base_weight
        glb_base_weight = 0
        floatval = float(filter_data) - glb_base_weight
        mydata = "{:10.3f}".format(floatval)
        mydata = mydata.rjust(20)
        self.scale_display.delete("1.0", END)
        self.scale_display.insert(END, mydata)

    def btn_clearlasttransaction_clicked(self):
        glb_sales.pop(-1)
        self.update_products_sold()

    def checkreyon(self, event: object):
        global glb_scaleId
        global glb_employeeselected

        self.message_box_text.delete("1.0", END)
        if glb_employeeselected != "":
            tt = self.select_reyon.get()
            glb_scaleId = self.select_reyon.current()
            teraziID = [x.teraziID for x in glb_reyons if x.ReyonName == tt][0]
            load_products(self, teraziID)
            for child in self.product_frame.winfo_children():
                child.destroy()
            self.product_frame_def()
            self.functions_frame_def()
            self.select_reyon.current(glb_scaleId)
            self.prdct_barcode.focus_set()
        else:
            self.message_box_text.insert(END, "Çalışan seçilmeden işleme devam edilemez")

    def employee_button_clicked(self, btn):
        global glb_scaleId
        global glb_employeeselected
        self.message_box_text.delete("1.0", END)
        glb_scaleId = self.select_reyon.current()
        if glb_scaleId != -1:
            glb_employeeselected = btn.cget("text")
            for child in self.product_frame.winfo_children():
                child.destroy()
            self.display_frame.grid(row=0, column=0, columnspan=2)
            self.products_sold_frame.grid(row=1, column=0, rowspan=2)
            self.product_frame.grid(row=1, column=1)
            self.paging_frame.grid(row=2, column=1)
            self.functions_frame.grid(row=3, column=0, columnspan=2)
            self.message_box_frame.grid(row=4, column=0, columnspan=2)
            self.functions_frame_def()
            self.employee_frame_def()
            self.paging_frame_def()
            self.productssold_frame_def()
            self.message_box_frame_def()
            tt = self.select_reyon.get()
            teraziID = [x.teraziID for x in glb_reyons if x.ReyonName == tt][0]
            load_products(self, teraziID)
            for child in self.product_frame.winfo_children():
                child.destroy()
            self.customer_frame_def()
            '''self.product_frame_def()'''
            self.functions_frame_def()
            self.select_reyon.current(glb_scaleId)
            sales_load(glb_customer_no, -1)
            self.update_products_sold()
            self.customer_no.delete('1.0', END)
            self.customer_no.insert(END, glb_customer_no)
            self.prdct_barcode.focus_set()
        else:
            self.message_box_text.insert(END, "Reyon Seçimini Yapmadan Personel Seçimi Yapılamaz")

    def update_products_sold(self):
        self.entry_products.delete("1.0", END)
        self.entry_calculatedtotal.delete("1.0", END)
        sum_calculated_price = 0
        for salesObj in glb_sales:
            self.entry_products.insert(END, salesObj.Name + "\n")
            calculated_price = float(salesObj.amount * salesObj.retailPrice)
            sum_calculated_price = sum_calculated_price + calculated_price
            myData = "{:.2f}".format(calculated_price).rjust(8, ' ') + "\n"
            self.entry_calculatedtotal.insert(END, myData)
        self.entry_sum.delete("1.0", END)
        self.entry_sum.insert(END, "{:5.2f}".format(sum_calculated_price).rjust(8, ' '))

    def product_button_clicked(self, btn):
        global glb_sales_line_id
        global glb_employeeselected
        global glb_customer_no

        if (glb_customer_no != 0):
            salesObj = Sales()
            salesObj.Name = btn.cget("text")
            salesObj.salesID = glb_customer_no
            salesObj.salesLineID = glb_sales_line_id
            glb_sales_line_id = glb_sales_line_id + 1
            salesObj.personelID = [x.personelID for x in glb_employees if x.Name == glb_employeeselected][0]
            salesObj.amount = float(self.scale_display.get("1.0", END).strip("\n"))
            salesObj.retailPrice = [x.price for x in glb_product_names if x.Name == salesObj.Name][0]
            salesObj.productID = [x.productID for x in glb_product_names if x.Name == salesObj.Name][0]
            salesObj.typeOfCollection = 0
            glb_sales.append(salesObj)
            self.update_products_sold()
        else:
            self.message_box_text.insert(END, "Yeni Müşteri Seçilmeden Ürün Seçimi Yapılamaz")

    def __init__(self, top=None):
        w, h = top.winfo_screenwidth(), root.winfo_screenheight()
        top.geometry("%dx%d+0+0" % (w, h))
        # top.geometry("800x480+1571+152")
        top.title("Terazi Ara Yüzü")
        top.configure(background="#d9d9d9")
        windows_env = 0
        serial_data = ''
        filter_data = ''
        update_period = 60
        serial_object = None
        loadTables()
        """Create frames"""
        self.display_frame = tk.Frame(top)
        self.products_sold_frame = tk.Frame(top)
        self.product_frame = tk.Frame(top)
        self.paging_frame = tk.Frame(top)
        self.functions_frame = tk.Frame(top)
        self.message_box_frame = tk.Frame(top)
        """define screen orientation"""
        self.display_frame.grid(row=0, column=0, columnspan=2)
        self.products_sold_frame.grid(row=1, column=0, rowspan=2)
        self.product_frame.grid(row=1, column=1)
        self.paging_frame.grid(row=2, column=1)
        self.functions_frame.grid(row=3, column=0, columnspan=2)
        self.message_box_frame.grid(row=4, column=0, columnspan=2)
        """define frame contents, except product frame glb_employees will be displayed in product frame"""
        self.display_frame_def()
        self.functions_frame_def()
        self.employee_frame_def()
        self.paging_frame_def()
        self.productssold_frame_def()
        self.message_box_frame_def()
        new_data = threading.Event()
        t2 = threading.Thread(target=update_gui, args=(self.scale_display, new_data,))
        t2.daemon = True
        t2.start()
        if windows_env:
            connect(new_data, 1, 9600, '5')
        else:
            connect(new_data, 2, 9600, 'USB0')


def connect(new_data, env, baud, port):
    """The function initiates the Connection to the UART device with the Port and Buad fed through the Entry
    boxes in the application.

    The radio button selects the platform, as the serial object has different key phrases
    for Linux and Windows. Some Exceptions have been made to prevent the app from crashing,
    such as blank entry fields and value errors, this is due to the state-less-ness of the
    UART device, the device sends data at regular intervals irrespective of the master's state.

    The other Parts are self explanatory.
    """

    global serial_object

    try:
        if env == 2:
            try:
                serial_object = serial.Serial('/dev/tty' + str(port), baud)
            except:
                print("Cant Open Specified Port")
        elif env == 1:
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
    global glb_base_weight

    while (1):
        event_is_set = new_data.wait()
        new_data.clear()
        if filter_data:
            scale_display.delete(1.0, END)
            floatval = float(filter_data) - glb_base_weight
            mydata = "{:10.3f}".format(floatval)
            mydata = mydata.rjust(20)
            scale_display.insert(END, mydata)


if __name__ == '__main__':
    vp_start_gui()
    glb_cursor.close()
