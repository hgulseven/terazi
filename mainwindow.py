import tkinter as tk
from tkinter import *
from tkinter.ttk import *
import threading
import serial
import datetime
import time
import requests
from datetime import datetime
import cursor
import mysql.connector
from mysql.connector import Error
import os

#Connection data
glb_host = "192.168.1.45"
glb_webHost = "192.168.1.45"
glb_database = "order_and_sales_management"
glb_user = "hakan"
glb_password = "QAZwsx135"
# queries
glb_GetTeraziProducts = """Select  TeraziID, productmodels.productID, productName, productRetailPrice from productmodels left outer join teraziscreenmapping on (teraziscreenmapping.productID=productmodels.productID) where TeraziID=%s order by screenSeqNo;"""
glb_SelectTerazi = "Select  TeraziID, teraziName from terazitable;"
glb_SelectEmployees = "Select personelID, persName,persSurname  from  employeesmodels;"
glb_SelectCounter ="""select counter from salescounter where salesDate=%s;"""
glb_UpdateCounter = """Update salescounter set counter=%s where salesDate=%s;"""
glb_InsertCounter = """Insert into salescounter (salesDate, counter) values (%s,%s);"""
glb_UpdateSales ="""update salesmodels set saleDate=%s, salesID=%s,  salesLineID=%s, personelID=%s, productID=%s, amount=%s, typeOfCollection=%s where salesID=%s and salesLineID=%s and typeOfCollection=%s and saleDate=%s;"""
glb_SelectSalesLineExists="""select count(*) from salesmodels where salesID=%s and typeOfCollection=%s and salesLineID=%s and saleDate=%s;"""
glb_UpdateSalesLine="""update salesmodels set saleDate=%s, salesID=%s,  salesLineID=%s, personelID=%s, productID=%s, amount=%s,typeOfCollection=%s where personelID=%s and typeOfCollection=%s and salesID=%s and salesLineID=%s and saleDate=%s;"""
glb_InsertSalesLine = """insert into salesmodels (saleDate, salesID,salesLineID,personelID,productID,amount,paidAmount,typeOfCollection) values (%s,%s,%s,%s,%s,%s,%s,%s);"""
glb_SelectSales = """select  saleDate, salesID,  salesLineID, personelID, salesmodels.productID, amount, productRetailPrice, productName, typeOfCollection from salesmodels left outer join productmodels on (salesmodels.productID= productmodels.productID) where salesId=%s and typeOfCollection=%s;"""
glb_SelectProductByBarcode ="""Select productID, productName, productRetailPrice from productmodels where productBarcodeID=%s;"""
glb_SelectCustomers = "Select distinct salesID from salesmodels where  typeOfCollection = -1 order by salesID;"
glb_SelectCustomersOnCashier = "Select  distinct salesID from salesmodels where  typeOfCollection = 0 order by salesID;"

glb_windows_env = 0 # 1 Windows 0 Linux
glb_cursor = 0  # global cursor for db access. Initialized in load_products
glb_customer_no = 0  # customer no is got by using salescounter table.
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
glb_scaleId = 0
glb_employees_selected = ''  # name of the selected employee.
glb_sales_line_id = 1  # line of the sales
glb_base_weight = 0  # tare weight is stored in this variable. Updated when tare button is clicked.
glb_product_page_count = 0  # paging of product buttons displayed in product frame
glb_employees_page_count = 0  # paging of employee buttons displayed in product frame
glb_active_customers_page_count = 0  # paging of active customers buttons displayed in product frame
glb_callback_customers_page_count = 0  # paging of callback customers buttons displayed in product frame

def add_to_log(self, function, err):
    if (os.path.isfile("log.txt")):
        fsize = os.stat('log.txt').st_size
        if fsize > 50000:
            os.rename('log.txt','log1.txt')
    with open('log.txt', 'a') as the_file:
        currentDate = datetime.now()
        the_file.write(currentDate.strftime("%Y-%m-%d %H:%M:%S")+ " "+function+" "+format(err)+"\n")

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


class salescounter(object):
    def __init__(self, salesDate=None, counter=None):
        self.salesDate = salesDate
        self.counter = 0

    def get_counter(self):
        global glb_host
        global glb_database
        global glb_user
        global glb_password
        global glb_SelectCounter
        global glb_UpdateCounter
        global glb_InsertCounter

        try:
            conn = mysql.connector.connect(host=glb_host,
                                           database=glb_database,
                                           user=glb_user,
                                           password=glb_password)  # pyodbc.connect(glb_connection_str)
            if conn.is_connected():
                myCursor = conn.cursor()
                my_date = datetime.now()
                myCursor.execute(glb_SelectCounter, (my_date.strftime('%Y-%m-%d'),))
                rows = myCursor.fetchall()
                number_of_rows = 0
                for row in rows:
                    number_of_rows = number_of_rows + 1
                    self.counter = row[0] + 1
                if number_of_rows > 0:
                   myCursor.execute(glb_UpdateCounter,(self.counter,my_date.strftime('%Y-%m-%d'),))
                else:
                    self.counter = 1
                    myCursor.execute(glb_InsertCounter,(my_date.strftime('%Y-%m-%d'),self.counter,))
                conn.commit()
                myCursor.close()
                conn.close()
            else:
                add_to_log(self, "get_Counter","Bağlantı Hatası")
        except Error as e:
            add_to_log(self, "get_Counter","DBError :"+e.msg)
        return self.counter


class Sales(object):
    def __init__(self, salesID=None, salesLineID=None, personelID=None, productID=None, Name=None,
                 retailPrice=None, amount=None, typeOfCollection=None):
        my_date = datetime.now()
        self.saleDate = my_date.strftime('%Y-%m-%d')
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


def sales_update(self, salesID, srcTypeOfCollection, destTypeOfCollection):
    global glb_host
    global glb_database
    global glb_user
    global glb_password
    global glb_UpdateSales

    try:
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            for salesObj in glb_sales:
                myCursor.execute(glb_UpdateSales,(salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID,salesObj.productID,
                                 salesObj.amount, destTypeOfCollection, salesID, salesObj.salesLineID, srcTypeOfCollection,
                                 salesObj.saleDate))
            conn.commit()
            myCursor.close()
            conn.close()
        else:
            add_to_log(self, "sales_Update","Bağlantı Hatası")
    except Error as e:
         add_to_log(self, "sales_update", "DbError :"+e.msg);



def sales_save(self, typeOfCollection):
    global glb_host
    global glb_database
    global glb_user
    global glb_password
    global glb_SelectSalesLineExists
    global glb_UpdateSalesLine
    global glb_InsertSalesLine

    try:
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            for salesObj in glb_sales:
                expectedTypeOfCollection=-1
                myCursor.execute(glb_SelectSalesLineExists,
                                 (salesObj.salesID,expectedTypeOfCollection,salesObj.salesLineID, salesObj.saleDate))
                number_of_rows = myCursor.fetchone()[0]
                if number_of_rows > 0:
                    myCursor.execute(glb_UpdateSalesLine,
                                     (salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID,
                                     salesObj.productID,salesObj.amount, typeOfCollection, salesObj.personelID,
                                     salesObj.typeOfCollection, salesObj.salesID,salesObj.salesLineID,salesObj.saleDate))
                    conn.commit()
                else:
                    paidAmount=0.0
                    myCursor.execute(glb_InsertSalesLine,
                                     (salesObj.saleDate, salesObj.salesID, salesObj.salesLineID,
                                      salesObj.personelID, salesObj.productID,salesObj.amount,paidAmount,typeOfCollection))
            conn.commit()
            myCursor.close()
            conn.close()
        else:
            add_to_log(self, "sales_save","Bağlantı Hatası")
    except Error as e:
        add_to_log(self, "sales_save","DBHatası :"+e.msg)


def sales_load(self,salesID, typeOfCollection):
    global glb_customer_no
    global glb_sales_line_id
    global glb_customer_no
    global glb_host
    global glb_database
    global glb_user
    global glb_password
    global glb_SelectSales

    try:
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            myCursor.execute(glb_SelectSales,
                             (salesID,typeOfCollection,))
            rows = myCursor.fetchall()
            glb_sales_line_id = 1
            for row in rows:
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
        else:
            add_to_log(self, "sales_load","Bağlantı Hatası")
    except Error as e:
        add_to_log(self, "sales_load","DBHatası :"+e.msg)


def get_product_based_on_barcod(self,prdct_barcode, salesObj):
    global glb_cursor
    global glb_sales_line_id
    global glb_customer_no
    global glb_employees_selected
    global glb_host
    global glb_database
    global glb_user
    global glb_password
    global glb_SelectProductByBarcode

    retval=1
    try:
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            myCursor.execute(glb_SelectProductByBarcode,
                             (prdct_barcode,))
            rows = myCursor.fetchall()
            if len(rows) > 0:
                for row in rows:
                    salesObj.salesID = glb_customer_no
                    salesObj.salesLineID = glb_sales_line_id
                    glb_sales_line_id = glb_sales_line_id + 1
                    salesObj.personelID = [x.personelID for x in glb_employees if x.Name == glb_employees_selected][0]
                    salesObj.productID = row[0]
                    salesObj.amount = 1
                    salesObj.Name = row[1]
                    salesObj.retailPrice = row[2]
                    salesObj.typeOfCollection = 0
            else:
                add_to_log(self, "get_product_based_on_barcod",prdct_barcode + " kayıt Buulunamadı")
                retval = 0
        else:
            add_to_log(self, "get_product_based_on_barcod","Bağlantı Hatası")
            retval = 0
    except Error as e:
        add_to_log(self, "get_product_based_on_barcod","DB Hatası :"+e.msg)
        retval = 0
    return retval

def get_served_customers(self):
    global glb_active_served_customers
    global glb_host
    global glb_database
    global glb_user

    global glb_password
    global glb_SelectCustomers

    try:
        glb_active_served_customers.clear()
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            myCursor.execute(glb_SelectCustomers)
            rows = myCursor.fetchall()
            for row in rows:
                customer_obj = Customer()
                customer_obj.Name = row[0]
                glb_active_served_customers.append(customer_obj)
            myCursor.close()
            conn.close()
        else:
            add_to_log(self, "get_served_Customers","Bağlantı Hatası")
    except Error as e:
        add_to_log(self, "get_served_Customers","DB Hatası :"+e.msg)


def get_customers_on_cashier(self):
    global glb_customers_on_cashier
    global glb_host
    global glb_database
    global glb_user
    global glb_password
    global glb_SelectCustomers

    try:
        glb_customers_on_cashier.clear()
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            myCursor.execute(glb_SelectCustomersOnCashier)
            rows = myCursor.fetchall()
            for row in rows:
                customer_obj = Customer()
                customer_obj.Name = row[0]
                glb_customers_on_cashier.append(customer_obj)
            myCursor.close()
            conn.close()
        else:
            add_to_log(self, "get_customers_on_cashier","Bağlantı Hatası")
    except Error as e:
        add_to_log(self, "get_customers_on_cashier","DB Hatası : "+e.msg)


def load_products(self, ID):
    global glb_host
    global glb_database
    global glb_user
    global glb_password

    try:
        conn = mysql.connector.connect(host = glb_host,
                                       database = glb_database,
                                       user = glb_user,
                                       password = glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            myCursor.execute(glb_GetTeraziProducts, (ID,))
            rows = myCursor.fetchall()
            glb_product_names.clear()
            for row in rows:
                productObj = Product()
                productObj.teraziID = row[0]
                productObj.productID = row[1]
                productObj.Name = row[2]
                productObj.price = float(row[3])
                glb_product_names.append(productObj)
            myCursor.close()
            conn.close()
        else:
            add_to_log(self, "load_products", "Bağlantı hatası")#Connect,on Error
    except Error as e:
        add_to_log(self, "load_products", "DB Error :"+e.msg) #any error log it

def WaitForSQL():
    db_connected = FALSE
    while not db_connected:
        try:
            conn =  mysql.connector.connect(host=glb_host,
                                            database='order_and_sales_management',
                                            user='hakan',
                                            password='QAZwsx135') # pyodbc.connect(glb_connection_str)
            if conn.is_connected():
                db_connected = TRUE
        except Error as e:
            db_connected = FALSE
            time.sleep(2)
    conn.close()


class loadTables:

    def __init__(self):
        global glb_scaleId
        global glb_sales_line_id
        global glb_base_weight
        global glb_customer_no
        global glb_cursor
        global glb_host
        global glb_database
        global glb_user
        global glb_password
        global glb_SelectTerazi

        WaitForSQL()
        load_products(self, 1)
        glb_scaleId = 0
        glb_sales_line_id = 1
        glb_base_weight = 0
        glb_customer_no = 0
        try:
            conn = mysql.connector.connect(host = glb_host,
                                           database = glb_database,
                                           user = glb_user,
                                           password = glb_password)  # pyodbc.connect(glb_connection_str)
            if conn.is_connected():
                myCursor = conn.cursor()
                myCursor.execute(glb_SelectTerazi)
                rows = myCursor.fetchall()
                for row in rows:
                    reyonObj = Reyon()
                    reyonObj.teraziID = row[0]
                    reyonObj.ReyonName = row[1]
                    glb_reyons.append(reyonObj)
                myCursor.close()
                myCursor=conn.cursor()
                myCursor.execute(glb_SelectEmployees)
                rows = myCursor.fetchall()
                for row in rows:
                    employeeObj = Employee()
                    employeeObj.Name = row[1] + " " + row[2]
                    employeeObj.personelID = row[0]
                    glb_employees.append(employeeObj)
                myCursor.close()
                conn.close()
            else:
                add_to_log(self, "LoadTables","Bağlantı Hatası")
        except Error as e:
            add_to_log(self, "LoadTables","DB error :"+e.msg)

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

class CustomerWindow(tk.Tk):
        def __init__(self,master):
            self.master=master
            new = tk.Frame.__init__(self)

#            new.mmessage_box_frame = tk.Frame(new)
#            new.message_box_frame.place(relx=0.0, rely=0.900, relheight=0.10, relwidth=0.994)
#            new.message_box_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9")
#            new.message_box_frame.configure(highlightbackground="#f0f0f0", width=795)
#            new.message_box_text = tk.Text(self.message_box_frame, height=1, width=80, font=("Arial Bold", 12),
#                                        bg='dark red', fg="white")
#            new.message_box_text.place(relx=0.0, rely=0.0, relheight=0.60, relwidth=0.994)


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
        self.paging_frame.place(relx=0.360, rely=0.560, relheight=0.120, relwidth=0.620)
        self.paging_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        next_button = tk.Button(self.paging_frame, text="Sonraki Sayfa")
        next_button.configure(activebackground="#ececec", activeforeground="#000000", background="dark red")
        next_button.configure(disabledforeground="#a3a3a3", font=font11, foreground="white")
        next_button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=3,
                              wraplength=130)
        next_button.configure(command=lambda btn=next_button: self.next_product_button_clicked())
        next_button.grid(row=0, column=2)
        previous_button = tk.Button(self.paging_frame, text="Önceki Sayfa")
        previous_button.configure(activebackground="#ececec", activeforeground="#000000", background="dark red")
        previous_button.configure(disabledforeground="#a3a3a3", font=font11, foreground="white")
        previous_button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=14, height=3,
                                  wraplength=130)
        previous_button.configure(command=lambda btn=previous_button: self.previous_product_button_clicked())
        previous_button.grid(row=0, column=0)

    def employee_frame_def(self):
        global top
        global glb_active_product_frame_content
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        glb_active_product_frame_content = 0
        varfunc = self.employee_button_clicked
        self.add_frame_buttons(0, self.product_frame,glb_employees,glb_employees_page_count,varfunc)

    def customer_frame_def(self):
        global glb_active_served_customers
        global top
        global glb_active_product_frame_content
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        glb_active_product_frame_content = 2
        get_served_customers(self)
        varfunc = self.customer_button_clicked
        self.add_frame_buttons(1, self.product_frame, glb_active_served_customers,glb_active_customers_page_count,varfunc)

    def call_back_customer_frame_def(self):
        global glb_customers_on_cashier
        global top
        global glb_active_product_frame_content
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        glb_active_product_frame_content = 3
        get_customers_on_cashier(self)
        varfunc = self.call_back_customer_no_clicked
        self.add_frame_buttons(0, self.product_frame,glb_customers_on_cashier,glb_callback_customers_page_count,varfunc)

    def display_frame_def(self):
        global top

        self.display_frame.place(relx=0.0, rely=0.0, relheight=0.100, relwidth=0.994)
        self.product_frame.configure(width=795)
        self.customer_no = tk.Text(self.display_frame, height=1, width=4, font=("Arial Bold", 25),
                                   bg='dark blue', fg="white")
        self.scale_display = tk.Text(self.display_frame, height=1, width=10, font=("Arial Bold", 25),
                                     bg='dark green', fg="white")
        self.scale_type = tk.Text(self.display_frame, height=1, width=3, font=("Arial Bold", 25),
                                  bg='dark green', fg="white")
        self.prdct_barcode = tk.Text(self.display_frame, height=1, width=2, font=('Arial Bold', 25))
        self.scale_type.insert(END, "Kg")
        self.customer_no.insert(END, "0")
        reyon_names = []
        for index, reyonObj in enumerate(glb_reyons):
            reyon_names.append(reyonObj.ReyonName)
        text_font = ('Arial Bold', '22')
        root.option_add('*TCombobox*Listbox.font', text_font)
        self.select_reyon = Combobox(self.display_frame, font=text_font, values=reyon_names)
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
        root.config(cursor="watch")
        root.update()
        textdata = self.prdct_barcode.get('1.0', END)
        textdata = textdata.rstrip("\n")
        textdata = textdata.lstrip("\n")
        self.prdct_barcode.delete('1.0', END)
        salesObj = Sales()
        if (get_product_based_on_barcod(self,textdata, salesObj)):
            glb_sales.append(salesObj)
        self.update_products_sold()
        root.config(cursor="")


    def add_frame_buttons(self, active_served_customers, frame, list, page_count, func):
        font11 = "-family {Segoe UI} -size 16 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        for child in frame.winfo_children():  # Clear frame contents whatever it is
            child.destroy()
        row_size, col_size = 6, 2  # grid in the frame is 4 by 3
        lower_cnt = page_count * row_size * col_size  # calculate lower bound in the list
        while lower_cnt > len(list):  # if lower bound is more than list size adjust it
            page_count = page_count - 1
            lower_cnt = page_count * row_size * col_size
        upper_cnt = lower_cnt + row_size * col_size  # calculate upper bound in the list
        if upper_cnt > len(list):  # if upper bound more than list size adjust it
            upper_cnt = len(list)
        btn_no = 0
        while lower_cnt < upper_cnt:
            obj = list[lower_cnt]
            button = tk.Button(frame, text=obj.Name)
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
            button.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
            button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=24, height=2,
                             wraplength=400)
            button.configure(command=lambda btn=button: func(btn))
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)
            btn_no = btn_no + 1
            lower_cnt = lower_cnt + 1
        if active_served_customers:
            btn_no = btn_no + 1
            button = tk.Button(self.product_frame, text="Yeni Müşteri")
            button.configure(command=lambda btn=button: self.new_customer_clicked())
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9",
                             disabledforeground="#a3a3a3")
            button.configure(font=font11, foreground="#000000", highlightbackground="#d9d9d9", highlightcolor="black",
                             pady="0", width=24, height=2)
            button.configure(wraplength=200)
            button.grid(row=int(btn_no / col_size), column=btn_no % col_size)
        return page_count

    def product_frame_def(self):
        global top
        global glb_active_product_frame_content
        global glb_product_page_count
        self.product_frame.place(relx=0.360, rely=0.110, relheight=0.440, relwidth=0.620)
        self.product_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9", width=635)
        glb_active_product_frame_content = 1
        varfunc = self.product_button_clicked
        glb_product_page_count = self.add_frame_buttons(0,self.product_frame, glb_product_names, glb_product_page_count, varfunc)

    def productssold_frame_def(self):
        global top
        font12 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        font10 = "-family {Segoe UI} -size 10 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        font9 = "-family {Segoe UI} -size 11 -weight bold -slant roman" \
                " -underline 0 -overstrike 0"
        self.products_sold_frame.place(relx=0.0, rely=0.110, relheight=0.550, relwidth=0.350)
        self.products_sold_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9",
                                           highlightbackground="#d9d9d9")
        self.products_sold_frame.configure(highlightcolor="black", width=155)
        self.entry_products = tk.Text(self.products_sold_frame)
        self.entry_products.place(relx=0.010, rely=0.02, relheight=0.84, relwidth=0.750)
        self.entry_products.configure(font=font10)
        self.entry_products.configure(takefocus="")
        self.entry_calculatedtotal = tk.Text(self.products_sold_frame)
        self.entry_calculatedtotal.tag_configure("right",justify=RIGHT)
        self.entry_calculatedtotal.tag_add("right",1.0,"end")
        self.entry_calculatedtotal.place(relx=0.750, rely=0.02, relheight=0.84, relwidth=0.240)
        self.entry_calculatedtotal.configure(font=font10, takefocus="")
        self.label_sum = tk.Label(self.products_sold_frame)
        self.label_sum.place(relx=0.040, rely=0.88, relheight=0.10, relwidth=0.300)
        # self.label_sum.configure(background="#d9d9d9")
        self.label_sum.configure(disabledforeground="#a3a3a3")
        self.label_sum.configure(font=font12)
        self.label_sum.configure(foreground="#000000")
        self.label_sum.configure(text='''Toplam''')
        self.entry_sum = tk.Text(self.products_sold_frame, height=1, width=80, font=font12)
        self.entry_sum.tag_configure("right",justify=RIGHT)
        self.entry_sum.tag_add("right",1.0,"end")
        self.entry_sum.place(relx=0.750, rely=0.88, relheight=0.10, relwidth=0.250)

    def functions_frame_def(self):
        global top
        font11 = "-family {Segoe UI} -size 15 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"

        self.functions_frame.place(relx=0.0, rely=0.700, relheight=0.200, relwidth=0.994)
        self.functions_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9")
        self.functions_frame.configure(highlightbackground="#f0f0f0", width=795)
        buttons_height = 65
        buttons_width = 250
        self.btn_dara = tk.Button(self.functions_frame)
        self.btn_dara.configure(command=lambda btn=self.btn_dara: self.btn_dara_clicked())
        self.btn_dara.place(relx=0.013, rely=0.050, height=buttons_height, width=buttons_width)
        self.btn_dara.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_dara.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_dara.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", text='''Dara''',
                                width=20)

        self.btn_changeuser = tk.Button(self.functions_frame)
        self.btn_changeuser.configure(command=lambda btn=self.btn_changeuser: self.btn_change_user_clicked())
        self.btn_changeuser.place(relx=0.264, rely=0.050, height=buttons_height, width=buttons_width)
        self.btn_changeuser.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_changeuser.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_changeuser.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                      text='''Çalışan Değiştir''', width=20)

        self.btn_call_back_customer = tk.Button(self.functions_frame)
        self.btn_call_back_customer.configure(
            command=lambda btn=self.btn_call_back_customer: self.call_back_customer_clicked())
        self.btn_call_back_customer.place(relx=0.516, rely=0.050, height=buttons_height, width=buttons_width)
        self.btn_call_back_customer.configure(activebackground="#ececec", activeforeground="#000000",
                                              background="#d9d9d9")
        self.btn_call_back_customer.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_call_back_customer.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                              text='''Müşteri Geri Çağır''', width=20)

        self.btn_cancelsale = tk.Button(self.functions_frame)
        self.btn_cancelsale.configure(command=lambda btn=self.btn_cancelsale: self.btn_cancelsale_clicked())
        self.btn_cancelsale.place(relx=0.767, rely=0.050, height=buttons_height, width=buttons_width)
        self.btn_cancelsale.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_cancelsale.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_cancelsale.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                      text='''Satışı İptal Et''', width=20)

        self.btn_cleardara = tk.Button(self.functions_frame)
        self.btn_cleardara.configure(command=lambda btn=self.btn_cleardara: self.btn_cleardara_clicked())
        self.btn_cleardara.place(relx=0.013, rely=0.500, height=buttons_height, width=buttons_width)
        self.btn_cleardara.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_cleardara.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000",
                                     text='''Darayı Temizle''', width=20)

        self.btn_savesale = tk.Button(self.functions_frame)
        self.btn_savesale.configure(command=lambda btn=self.btn_savesale: self.btn_savesale_clicked())
        self.btn_savesale.place(relx=0.264, rely=0.500, height=buttons_height, width=buttons_width)
        self.btn_savesale.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_savesale.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000",
                                    text='''Satışı Kaydet''', width=20)

        self.btn_sendcashier = tk.Button(self.functions_frame)
        self.btn_sendcashier.configure(command=lambda btn=self.btn_sendcashier: self.btn_send_cashier_clicked())
        self.btn_sendcashier.place(relx=0.516, rely=0.500, height=buttons_height, width=buttons_width)
        self.btn_sendcashier.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_sendcashier.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_sendcashier.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                       text='''Kasaya Gönder''', width=20)

        self.btn_clearlasttransaction = tk.Button(self.functions_frame)
        self.btn_clearlasttransaction.configure(
            command=lambda btn=self.btn_clearlasttransaction: self.btn_clearlasttransaction_clicked())
        self.btn_clearlasttransaction.place(relx=0.767, rely=0.500, height=buttons_height, width=buttons_width)
        self.btn_clearlasttransaction.configure(activebackground="#ececec", activeforeground="#000000",
                                                background="#d9d9d9")
        self.btn_clearlasttransaction.configure(disabledforeground="#a3a3a3", font=font11, foreground="#000000")
        self.btn_clearlasttransaction.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                                text='''Son İşlemi Sil''', width=20)

    def next_product_button_clicked(self):
        global glb_product_page_count
        global glb_callback_customers_page_count
        global glb_active_customers_page_count
        global glb_employees_page_count
        global glb_active_product_frame_content
        root.config(cursor="watch")
        root.update()
        if glb_active_product_frame_content == 0:  # Middle frame is used for employees
            glb_employees_page_count = glb_employees_page_count + 1
            varfunc = self.employee_button_clicked
            glb_employees_page_count = self.add_frame_buttons(0, self.product_frame,glb_employees,glb_employees_page_count, varfunc)
        elif glb_active_product_frame_content == 1:  # Middle frame is used for products
            glb_product_page_count = glb_product_page_count + 1
            varfunc = self.product_button_clicked
            glb_product_page_count = self.add_frame_buttons(0, self.product_frame,glb_product_names,glb_product_page_count, varfunc)
        elif glb_active_product_frame_content == 2:  # Middle frame is used for customers
             glb_active_customers_page_count = glb_active_customers_page_count + 1
             varfunc = self.customer_button_clicked
             glb_active_customers_page_count = self.add_frame_buttons(1, self.product_frame,glb_active_served_customers,glb_active_customers_page_count, varfunc)
        else:  # Middle frame for callback customers
            glb_callback_customers_page_count = glb_callback_customers_page_count + 1
            varfunc = self.call_back_customer_no_clicked
            glb_callback_customers_page_count = self.add_frame_buttons(0, self.product_frame,glb_customers_on_cashier,glb_callback_customers_page_count, varfunc)
        root.config(cursor="")

    def previous_product_button_clicked(self):
        global glb_product_page_count
        global glb_callback_customers_page_count
        global glb_active_customers_page_count
        global glb_employees_page_count
        global glb_active_product_frame_content
        root.config(cursor="watch")
        root.update()
        if glb_active_product_frame_content == 0:  # Middle frame is used for employees
            if glb_employees_page_count > 0:
                glb_employees_page_count = glb_employees_page_count - 1
            varfunc = self.employee_button_clicked
            glb_employees_page_count = self.add_frame_buttons(0, self.product_frame, glb_employees, glb_employees_page_count, varfunc)
        elif glb_active_product_frame_content == 1:  # Middle frame is used for products
            if glb_product_page_count > 0:
                glb_product_page_count = glb_product_page_count - 1
            varfunc = self.product_button_clicked
            glb_product_page_count = self.add_frame_buttons(0, self.product_frame,glb_product_names,glb_product_page_count, varfunc)
        elif glb_active_product_frame_content == 2:  # Middle frame is used for customers
            if glb_active_customers_page_count > 0:
                glb_active_customers_page_count = glb_active_customers_page_count -1
            varfunc = self.customer_button_clicked
            glb_active_customers_page_count = self.add_frame_buttons(1, self.product_frame,glb_active_served_customers,glb_active_customers_page_count, varfunc)
        else:  # Middle frame for callback customers
            if glb_callback_customers_page_count > 0:
               glb_callback_customers_page_count = glb_callback_customers_page_count - 1
            varfunc = self.call_back_customer_no_clicked
            glb_callback_customers_page_count = self.add_frame_buttons(0, self.product_frame,glb_customers_on_cashier,glb_callback_customers_page_count, varfunc)
        root.config(cursor="")

    def customer_button_clicked(self, btn):
        global glb_customer_no
        root.config(cursor="watch")
        root.update()
        glb_customer_no = btn.cget("text")
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        sales_load(self,glb_customer_no, -1)
        self.product_frame_def()
        self.update_products_sold()
        self.update_products_sold_for_customer()
        root.config(cursor="")

    def btn_send_cashier_clicked(self):
        global glb_customer_no
        global glb_sales_line_id
        root.config(cursor="watch")
        root.update()
        sales_save(self,-1)
        sales_update(self,glb_customer_no, -1,
                     0)  # update which has value -1 (actively served customer) to 0 (sent to cashier)
        glb_sales.clear()
        self.update_products_sold()
        self.update_products_sold_for_customer()
        glb_customer_no = 0
        glb_sales_line_id = 1
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, "0")
        resp = requests.get("http://"+glb_webHost+"/api/DataRefresh")
        self.btn_cleardara_clicked()
        self.new_customer_clicked()
        root.config(cursor="")

    def btn_change_user_clicked(self):
        global top
        global glb_employees_selected
        global glb_customer_no
        root.config(cursor="watch")
        root.update()
        glb_sales.clear()
        glb_customer_no = 0
        self.update_products_sold()
        self.update_products_sold_for_customer()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        self.employee_frame_def()
        glb_employees_selected = ""
        root.config(cursor="")

    def call_back_customer_no_clicked(self, btn):
        root.config(cursor="watch")
        root.update()
        salesID = btn.cget("text")
        glb_sales.clear()
        sales_load(self,salesID, 0)
        sales_update(self,salesID, 0, -1)
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        self.update_products_sold()
        self.update_products_sold_for_customer()
        self.product_frame_def()
        resp = requests.get("http://"+glb_webHost+"/api/DataRefresh")
        root.config(cursor="")

    def call_back_customer_clicked(self):
        root.config(cursor="watch")
        root.update()
        self.call_back_customer_frame_def()
        root.config(cursor="")

    def new_customer_clicked(self):
        global top
        global glb_sales_line_id
        global glb_employees_selected
        global glb_customer_no
        root.config(cursor="watch")
        root.update()
        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        salescounterobj = salescounter()
        glb_customer_no = salescounterobj.get_counter()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        glb_sales_line_id = 1
        self.product_frame_def()
        root.config(cursor="")

    def btn_cancelsale_clicked(self):
        global top
        global glb_sales_line_id
        global glb_employees_selected
        global glb_customer_no
        root.config(cursor="watch")
        root.update()
        sales_save(self,-2)
        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        self.update_products_sold()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, "0")
        glb_sales_line_id = 1
        glb_customer_no = 0
        self.new_customer_clicked()
        root.config(cursor="")

    def btn_savesale_clicked(self):
        global glb_sales_line_id
        root.config(cursor="watch")
        root.update()
        sales_save(self,-1)
#        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        self.update_products_sold()
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, "0")
        glb_sales_line_id = 1
        self.btn_change_user_clicked()
        root.config(cursor="")

    def btn_dara_clicked(self):
        global glb_base_weight
        root.config(cursor="watch")
        root.update()
        glb_base_weight = glb_base_weight + float(self.scale_display.get("1.0", END).strip("\n"))
        self.scale_display.delete("1.0", END)
        self.scale_display.insert(END, "0.000".rjust(20))
        root.config(cursor="")

    def btn_cleardara_clicked(self):
        global glb_base_weight
        root.config(cursor="watch")
        root.update()
        glb_base_weight = 0
        floatval = float(filter_data) - glb_base_weight
        mydata = "{:10.3f}".format(floatval)
        mydata = mydata.rjust(20)
        self.scale_display.delete("1.0", END)
        self.scale_display.insert(END, mydata)
        root.config(cursor="")

    def btn_clearlasttransaction_clicked(self):
        root.config(cursor="watch")
        root.update()
        glb_sales.pop(-1)
        self.update_products_sold()
        self.update_products_sold_for_customer()
        root.config(cursor="")

    def checkreyon(self, event: object):
        global glb_scaleId
        global glb_employees_selected
        root.config(cursor="watch")
        root.update()
        self.message_box_text.delete("1.0", END)
        if glb_employees_selected != "":
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
        root.config(cursor="")

    def employee_button_clicked(self, btn):
        global glb_scaleId
        global glb_employees_selected
        root.config(cursor="watch")
        root.update()
        self.message_box_text.delete("1.0", END)
        glb_scaleId = self.select_reyon.current()
        if glb_scaleId != -1:
            glb_employees_selected = btn.cget("text")
            for child in self.product_frame.winfo_children():
                child.destroy()
            self.display_frame.grid(row=0, column=0, columnspan=2)
            self.products_sold_frame.grid(row=1, column=0, rowspan=2)
            self.product_frame.grid(row=1, column=1)
            self.paging_frame.grid(row=2, column=1)
            self.functions_frame.grid(row=3, column=0, columnspan=2)
            self.message_box_frame.grid(row=4, column=0, columnspan=2)
            self.product_frame_def()
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
            sales_load(self,glb_customer_no, -1)
            self.update_products_sold()
            self.customer_no.delete('1.0', END)
            self.customer_no.insert(END, glb_customer_no)
            self.prdct_barcode.focus_set()
        else:
            self.message_box_text.insert(END, "Reyon Seçimini Yapmadan Personel Seçimi Yapılamaz")
        root.config(cursor="")

    def update_products_sold(self):
        self.entry_products.delete("1.0", END)
        self.entry_calculatedtotal.delete("1.0", END)
        sum_calculated_price = 0
        for salesObj in glb_sales:
            self.entry_products.insert(END, " "+salesObj.Name + "\n")
            calculated_price = float(salesObj.amount * float(salesObj.retailPrice))
            sum_calculated_price = sum_calculated_price + calculated_price
            myData = "{:.2f}\n".format(calculated_price).rjust(8, ' ')
            self.entry_calculatedtotal.insert(END, myData,"right")
        self.entry_sum.delete("1.0", END)
        self.entry_sum.insert(END, "{:5.2f}".format(sum_calculated_price).rjust(8, ' '),"right")

    def update_products_sold_for_customer(self):
        self.newWindow.products_sold.delete("1.0", END)
        self.newWindow.products_sold_amount.delete("1.0", END)
        self.newWindow.products_sold_price.delete("1.0", END)
        sum_calculated_price = 0
        for salesObj in glb_sales:
            self.newWindow.products_sold.insert(END, salesObj.Name + "\n")
            self.newWindow.products_sold_amount.insert(END,"{:.3f}\n".format(salesObj.amount).rjust(8, ' '),"right")
            calculated_price = float(salesObj.amount * float(salesObj.retailPrice))
            sum_calculated_price = sum_calculated_price + calculated_price
            myData = "{:.2f}\n".format(calculated_price).rjust(8, ' ')
            self.newWindow.products_sold_price.insert(END, myData,"right")
        self.newWindow.products_sold_total.delete("1.0", END)
        self.newWindow.products_sold_total.insert(END, "{:.2f}".format(sum_calculated_price).rjust(8, ' '),"right")

    def product_button_clicked(self, btn):
        global glb_sales_line_id
        global glb_employees_selected
        global glb_customer_no

        if (glb_customer_no != 0):
            salesObj = Sales()
            salesObj.Name = btn.cget("text")
            salesObj.salesID = glb_customer_no
            salesObj.salesLineID = glb_sales_line_id
            glb_sales_line_id = glb_sales_line_id + 1
            salesObj.personelID = [x.personelID for x in glb_employees if x.Name == glb_employees_selected][0]
            salesObj.amount = float(self.scale_display.get("1.0", END).strip("\n"))
            salesObj.retailPrice = [x.price for x in glb_product_names if x.Name == salesObj.Name][0]
            salesObj.productID = [x.productID for x in glb_product_names if x.Name == salesObj.Name][0]
            salesObj.typeOfCollection = 0
            glb_sales.append(salesObj)
            self.update_products_sold()
            self.update_products_sold_for_customer()
        else:
            self.message_box_text.insert(END, "Yeni Müşteri Seçilmeden Ürün Seçimi Yapılamaz")

    def __init__(self, top=None):
        w, h = top.winfo_screenwidth()/2, root.winfo_screenheight()
        top.geometry("%dx%d+0+0" % (w, h))
        # top.geometry("800x480+1571+152")
        top.title("Terazi Ara Yüzü")
        top.configure(background="#d9d9d9")
        serial_data = ''
        filter_data = ''
        update_period = 60
        serial_object = None
        """Create frames"""
        self.master=top
        self.display_frame = tk.Frame(top)
        self.products_sold_frame = tk.Frame(top)
        self.product_frame = tk.Frame(top)
        self.paging_frame = tk.Frame(top)
        self.functions_frame = tk.Frame(top)
        self.message_box_frame = tk.Frame(top)
        self.message_box_frame_def()
        loadTables()
        """define screen orientation"""
        self.display_frame.grid(row=0, column=0, columnspan=2)
        self.products_sold_frame.grid(row=1, column=0, rowspan=2)
        self.product_frame.grid(row=1, column=1)
        self.paging_frame.grid(row=2, column=1)
        self.functions_frame.grid(row=3, column=0, columnspan=2)
        self.message_box_frame.grid(row=4, column=0, columnspan=2)
        """define frame contents, except product frame glb_employees will be displayed in product frame"""
        self.product_frame_def()
        self.display_frame_def()
        self.functions_frame_def()
        self.employee_frame_def()
        self.paging_frame_def()
        self.productssold_frame_def()
        new_data = threading.Event()
        t2 = threading.Thread(target=update_gui, args=(self.scale_display, new_data,))
        t2.daemon = True
        t2.start()
        if glb_windows_env:
            connect(self, new_data, 1, 9600, '6')
        else:
            connect(self, new_data, 2, 9600, 'USB0')

        font18 = "-family {Segoe UI} -size 18 -slant " \
                 "roman -underline 0 -overstrike 0"
        font9 = "-family {Segoe UI} -size 11 -weight bold -slant roman" \
                " -underline 0 -overstrike 0"
        self.newWindow = tk.Toplevel(self.master)
        self.newWindow.geometry("%dx%d+1200+0" % (w, h))
        self.newWindow.attributes("-fullscreen", True)
        self.newWindow.title("Müşteri Bilgi Ekranı")
#        load = Image.open("logo.png")
#        render = ImageTk.PhotoImage(load)
#        img = Label(self.newWindow, image=render)
#        img.place(relx=0.300, rely=0.01, relheight=0.09, relwidth=0.50)
#        img.image = render
        self.newWindow.company_label = tk.Label(self.newWindow,height=1,width=30,font=font18)
        self.newWindow.company_label.place(relx=0.40, rely=0.0, relheight=0.05, relwidth=0.200)
        self.newWindow.company_label.config(text='''G Ü L S E V EN''',fg='dark red')
        self.newWindow.products_sold_label = tk.Label(self.newWindow,height=1,width=30,font=font18)
        self.newWindow.products_sold_label.place(relx=0.010, rely=0.05, relheight=0.1, relwidth=0.700)
        self.newWindow.products_sold_label.config(text=''' Ürün''',anchor=W,bg='dark red',fg='white')
        self.newWindow.products_sold = tk.Text(self.newWindow, height=2, width=30)
        self.newWindow.products_sold.place(relx=0.010, rely=0.16, relheight=0.70, relwidth=0.700)
        self.newWindow.products_sold.configure(font=font18)
        self.newWindow.products_sold.configure(takefocus="")
        self.newWindow.products_sold_amount_label = tk.Label(self.newWindow,height=1,width=30,font=font18)
        self.newWindow.products_sold_amount_label.place(relx=0.720, rely=0.05, relheight=0.1, relwidth=0.10)
        self.newWindow.products_sold_amount_label.config(text='''Miktar ''',anchor=E,bg='dark red',fg='white')
        self.newWindow.products_sold_amount = tk.Text(self.newWindow, height=2, width=10)
        self.newWindow.products_sold_amount.tag_configure("right",justify=RIGHT)
        self.newWindow.products_sold_amount.tag_add("right",1.0,"end")
        self.newWindow.products_sold_amount.place(relx=0.720,rely=0.16,relheight=0.70,relwidth=0.10)
        self.newWindow.products_sold_amount.configure(font=font18)
        self.newWindow.products_sold_price_label = tk.Label(self.newWindow,height=1,width=30,font=font18)
        self.newWindow.products_sold_price_label.place(relx=0.830, rely=0.05, relheight=0.1, relwidth=0.15)
        self.newWindow.products_sold_price_label.config(text='''Tutar ''',anchor=E,bg='dark red', fg='white')
        self.newWindow.products_sold_price= tk.Text(self.newWindow, height=2, width=10)
        self.newWindow.products_sold_price.tag_configure("right",justify=RIGHT)
        self.newWindow.products_sold_price.tag_add("right",1.0,"end")
        self.newWindow.products_sold_price.place(relx=0.830,rely=0.16,relheight=0.70,relwidth=0.15)
        self.newWindow.products_sold_price.configure(font=font18)
        self.newWindow.products_sold_total_label = tk.Label(self.newWindow,height=1,width=30,font=font18)
        self.newWindow.products_sold_total_label.place(relx=0.720, rely=0.87, relheight=0.1, relwidth=0.10)
        self.newWindow.products_sold_total_label.config(text=''' TOPLAM ''',anchor=NW,bg='dark red',fg='white')
        self.newWindow.products_sold_total= tk.Text(self.newWindow, height=2, width=10)
        self.newWindow.products_sold_total.tag_configure("right",justify=RIGHT)
        self.newWindow.products_sold_total.tag_add("right",1.0,"end")
        self.newWindow.products_sold_total.place(relx=0.830,rely=0.87,relheight=0.10,relwidth=0.15)
        self.newWindow.products_sold_total.configure(font=font18,bg='dark red',fg='white')

def connect(self, new_data, env, baud, port):
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
            serial_object = serial.Serial(port='/dev/tty' + str(port), baudrate=baud)
        elif env == 1:
            serial_object = serial.Serial('COM' + str(port), baud)
    except ValueError:
        print("Enter Baud and Port")
        return
    t1 = threading.Thread(target=get_data,
                          args=(self, new_data,))
    t1.daemon = True
    t1.start()


def get_data(self, new_data):
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
        except NameError as err:
            add_to_log(self, "Get data", err)
            pass
        except TypeError as err:
            add_to_log(self, "Get data", err)
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
            mydata = mydata.rjust(13)
            scale_display.insert(END, mydata)


if __name__ == '__main__':
    vp_start_gui()
