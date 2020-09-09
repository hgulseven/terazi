import datetime
import os
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import *
import mysql.connector
import requests
import serial
from mysql.connector import Error
"""Connection data"""
glb_host = "192.168.1.45"
glb_webHost = "192.168.1.45"
glb_database = "order_and_sales_management"
glb_user = "hakan"
glb_password = "QAZwsx135"
glb_locationid = ""
glb_serial_object = None
w = None
top_level=None
root = None

# queries
glb_GetTeraziProducts = "Select  TeraziID, productmodels.productID, productName, productRetailPrice,productBarcodeID from productmodels left outer join " \
                        "teraziscreenmapping on (teraziscreenmapping.productID=productmodels.productID) where TeraziID=%s order by screenSeqNo;"
glb_SelectTerazi = "Select  TeraziID, teraziName from terazitable;"
glb_SelectEmployees = "Select personelID, persName,persSurname  from  employeesmodels;"
glb_SelectCounter = "select counter from salescounter where salesDate=%s and locationID=%s;"
glb_UpdateCounter = "Update salescounter set counter=%s where salesDate=%s and locationID=%s;"
glb_InsertCounter = "Insert into salescounter (salesDate, counter,locationID) values (%s,%s,%s);"
glb_UpdateSales = "update salesmodels set saleDate=%s, salesID=%s,  salesLineID=%s, personelID=%s, productID=%s, amount=%s, typeOfCollection=%s, saleTime=%s, locationID=%s,dara=%s where salesID=%s and salesLineID=%s and typeOfCollection=%s and saleDate=%s and locationID=%s;"
glb_SelectSalesLineExists = "select count(*) from salesmodels where salesID=%s and salesLineID=%s and saleDate=%s and locationID=%s;"
glb_UpdateSalesLine = "update salesmodels set saleDate=%s, salesID=%s,  salesLineID=%s, personelID=%s, productID=%s, amount=%s,typeOfCollection=%s,locationID=%s,dara=%s where personelID=%s and salesID=%s and salesLineID=%s and saleDate=%s and locationID=%s;"
glb_InsertSalesLine = "insert into salesmodels (saleDate, salesID,salesLineID,personelID,productID,amount,paidAmount,typeOfCollection,locationID,dara) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"
glb_SelectSales = "select  saleDate, salesID,  salesLineID, personelID, salesmodels.productID, amount, productRetailPrice, productName, typeOfCollection,dara from salesmodels left outer join productmodels on (salesmodels.productID= productmodels.productID) where salesId=%s and typeOfCollection=%s and locationID=%s;"
glb_SelectProductByBarcode = "Select productID, productName, productRetailPrice from productmodels where productBarcodeID=%s;"
glb_SelectCustomers = "Select distinct salesID from salesmodels where  saleDate=%s and typeOfCollection = -1 and locationID=%s order by salesID;"
glb_SelectCustomersOnCashier = "Select  distinct salesID from salesmodels where  saleDate=%s and typeOfCollection = 0 and locationID=%s order by salesID;"
glb_salesDelete = "delete from salesmodels where saleDate=%s and salesID=%s and locationID=%s;"

glb_windows_env = 1  # 1 Windows 0 Linux
glb_cursor = 0  # global cursor for db access. Initialized in load_products
glb_customer_no = 0  # customer no is got by using salescounter table.
glb_filter_data =""
glb_screensize = 1200
top = None
glb_product_names = []  # products are loaded to memory based on rayon
glb_reyonlar = []  # rayon combobox contents
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


def add_to_log(function, err):
    global glb_windows_env

    if glb_windows_env == 1:
        logpath = "c:\\users\\hakan\\PycharmProjects\\terazi\\"
    else:
        logpath = "/home/pi/PycharmProjects/terazi/"
    if os.path.isfile(logpath+'log.txt'):
        fsize = os.stat(logpath+'log.txt').st_size
        if fsize > 50000:
            os.rename(logpath+'log.txt', logpath+'log1.txt')
    with open(logpath+'log.txt', 'a') as the_file:
        current_date = datetime.now()
        the_file.write(current_date.strftime("%Y-%m-%d %H:%M:%S") + " " + function + " " + format(err) + "\n")
    the_file.close()

class Product(object):
    def __init__(self, productID=None, Name=None, price=None, teraziID=None, productBarcodeID=None):
        self.productID = productID
        self.Name = Name
        self.price = price
        self.teraziID = teraziID
        self.productBarcodeID=productBarcodeID


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

    def get_counter(self):
        global glb_host
        global glb_database
        global glb_user
        global glb_password
        global glb_SelectCounter
        global glb_UpdateCounter
        global glb_InsertCounter
        global glb_locationid

        try:
            conn = mysql.connector.connect(host=glb_host,
                                           database=glb_database,
                                           user=glb_user,
                                           password=glb_password)  # pyodbc.connect(glb_connection_str)
            if conn.is_connected():
                myCursor = conn.cursor()
                my_date = datetime.now()
                myCursor.execute(glb_SelectCounter, (my_date.strftime('%Y-%m-%d'), glb_locationid,))
                rows = myCursor.fetchall()
                number_of_rows = 0
                for row in rows:
                    number_of_rows = number_of_rows + 1
                    self.counter = row[0] + 1
                if number_of_rows > 0:
                    myCursor.execute(glb_UpdateCounter, (self.counter, my_date.strftime('%Y-%m-%d'), glb_locationid,))
                else:
                    self.counter = 1
                    myCursor.execute(glb_InsertCounter, (my_date.strftime('%Y-%m-%d'), self.counter, glb_locationid,))
                conn.commit()
                myCursor.close()
                conn.close()
            else:
                add_to_log("get_Counter", "Bağlantı Hatası")
        except Error as e:
            add_to_log("get_Counter", "DBError :" + e.msg)
        return self.counter


class Sales(object):
    def __init__(self, salesID=None, salesLineID=None, personelID=None, productID=None, Name=None,
                 retailPrice=None, amount=None, typeOfCollection=None, productBarcodeID=None):
        global glb_base_weight
        global glb_locationid

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
        self.locationID = glb_locationid
        self.dara = glb_base_weight
        self.productBarcodeID=productBarcodeID


def sales_update(srcTypeOfCollection, destTypeOfCollection):
    global glb_host
    global glb_database
    global glb_user
    global glb_password
    global glb_UpdateSales
    global glb_base_weight
    global glb_locationid

    try:
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            for salesObj in glb_sales:
                my_date = datetime.now()
                saleTime = my_date.strftime('%Y-%m-%d %H:%M:%S.%f')
                myCursor.execute(glb_UpdateSales, (salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID, salesObj.productID, salesObj.amount, destTypeOfCollection, saleTime, glb_locationid, glb_base_weight, salesObj.salesID, salesObj.salesLineID, srcTypeOfCollection, salesObj.saleDate, glb_locationid,))
            conn.commit()
            myCursor.close()
            conn.close()
        else:
            add_to_log("sales_Update", "Bağlantı Hatası")
    except Error as e:
        add_to_log("sales_update", "DbError :"+e.msg)


def sales_hard_delete( salesID):
    global glb_salesDelete
    global glb_locationid

    try:
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            my_date = datetime.now()
            saleDate = my_date.strftime('%Y-%m-%d')
            myCursor.execute(glb_salesDelete,(saleDate,salesID,glb_locationid,))
            conn.commit()
            myCursor.close()
            conn.close()
        else:
            add_to_log("sales_hard_delete","Bağlantı Hatası")
    except Error as e:
        add_to_log("sales_hard_delete","DBHatası :"+e.msg)


def sales_save(typeOfCollection):
    global glb_host
    global glb_database
    global glb_user
    global glb_password
    global glb_SelectSalesLineExists
    global glb_UpdateSalesLine
    global glb_InsertSalesLine
    global glb_locationid
    global glb_base_weight

    try:
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            for salesObj in glb_sales:
                myCursor.execute(glb_SelectSalesLineExists,
                                 (salesObj.salesID,salesObj.salesLineID, salesObj.saleDate,glb_locationid))
                number_of_rows = myCursor.fetchall()[0][0]
                if number_of_rows > 0:
                    myCursor.execute(glb_UpdateSalesLine,
                                     (salesObj.saleDate, salesObj.salesID, salesObj.salesLineID, salesObj.personelID,
                                     salesObj.productID,salesObj.amount, typeOfCollection,glb_locationid,glb_base_weight, salesObj.personelID,
                                     salesObj.salesID,salesObj.salesLineID,salesObj.saleDate,glb_locationid))
                else:
                    paidAmount=0.0
                    myCursor.execute(glb_InsertSalesLine,
                                     (salesObj.saleDate, salesObj.salesID, salesObj.salesLineID,
                                      salesObj.personelID, salesObj.productID,salesObj.amount,paidAmount,typeOfCollection,glb_locationid,glb_base_weight))
            conn.commit()
            myCursor.close()
            conn.close()
        else:
            add_to_log("sales_save","Bağlantı Hatası")
    except Error as e:
        add_to_log("sales_save","DBHatası :"+e.msg)


def sales_load(salesID, typeOfCollection):
    global glb_customer_no
    global glb_sales_line_id
    global glb_customer_no
    global glb_host
    global glb_database
    global glb_user
    global glb_password
    global glb_SelectSales
    global glb_locationid
    global glb_base_weight

    try:
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            myCursor.execute(glb_SelectSales,
                             (salesID,typeOfCollection,glb_locationid))
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
                salesObj.dara=row[9]
                glb_base_weight = salesObj.dara
                glb_sales.append(salesObj)
                glb_sales_line_id = glb_sales_line_id + 1
            myCursor.close()
            conn.close()
        else:
            add_to_log("sales_load","Bağlantı Hatası")
    except Error as e:
        add_to_log("sales_load","DBHatası :"+e.msg)


def get_product_based_on_barcod(prdct_barcode, salesObj):
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
                add_to_log("get_product_based_on_barcod",prdct_barcode + " kayıt Buulunamadı")
                retval = 0
            myCursor.close()
            conn.close()
        else:
            add_to_log("get_product_based_on_barcod","Bağlantı Hatası")
            retval = 0
    except Error as e:
        add_to_log("get_product_based_on_barcod","DB Hatası :"+e.msg)
        retval = 0
    return retval

def get_served_customers():
    global glb_active_served_customers
    global glb_host
    global glb_database
    global glb_user
    global glb_password
    global glb_SelectCustomers
    global glb_locationid

    try:
        glb_active_served_customers.clear()
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():

            myCursor = conn.cursor()
            my_date = datetime.now()
            saleDate = my_date.strftime('%Y-%m-%d')
            myCursor.execute(glb_SelectCustomers, (saleDate, glb_locationid,))
            rows = myCursor.fetchall()
            for row in rows:
                customer_obj = Customer()
                customer_obj.Name = row[0]
                glb_active_served_customers.append(customer_obj)
            myCursor.close()
            conn.close()
        else:
            add_to_log("get_served_Customers","Bağlantı Hatası")
    except Error as e:
        add_to_log("get_served_Customers","DB Hatası :"+e.msg)


def get_customers_on_cashier():
    global glb_customers_on_cashier
    global glb_host
    global glb_database
    global glb_user
    global glb_password
    global glb_locationid

    try:
        glb_customers_on_cashier.clear()
        conn = mysql.connector.connect(host=glb_host,
                                       database=glb_database,
                                       user=glb_user,
                                       password=glb_password)  # pyodbc.connect(glb_connection_str)
        if conn.is_connected():
            myCursor = conn.cursor()
            my_date = datetime.now()
            saleDate = my_date.strftime('%Y-%m-%d')
            myCursor.execute(glb_SelectCustomersOnCashier, (saleDate, glb_locationid,))
            rows = myCursor.fetchall()
            for row in rows:
                customer_obj = Customer()
                customer_obj.Name = row[0]
                glb_customers_on_cashier.append(customer_obj)
            myCursor.close()
            conn.close()
        else:
            add_to_log("get_customers_on_cashier","Bağlantı Hatası")
    except Error as e:
        add_to_log("get_customers_on_cashier","DB Hatası : "+e.msg)


def load_products(ID):
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
                productObj.productBarcodeID=row[4]
                glb_product_names.append(productObj)
            myCursor.close()
            conn.close()
        else:
            add_to_log( "load_products", "Bağlantı hatası")#Connect,on Error
    except Error as e:
        add_to_log("load_products", "DB Error :"+e.msg) #any error log it

def wait_for_sql():
    db_connected = FALSE
    while not db_connected:
        try:
            conn =  mysql.connector.connect(host=glb_host,
                                            database='order_and_sales_management',
                                            user='hakan',
                                            password='QAZwsx135') # pyodbc.connect(glb_connection_str)
            if conn.is_connected():
                db_connected = TRUE
            conn.close()
        except Error as e:
            add_to_log("wait_for_sql", e.msg)
            messagebox.showinfo("Hata Mesajı", "Sunucu ile bağlantı Kurulamadı "+ e.msg)
            db_connected = FALSE
            time.sleep(2)


class load_tables:

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

        wait_for_sql()
        load_products(1)
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
                    glb_reyonlar.append(reyonObj)
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
                add_to_log("load_tables","Bağlantı Hatası")
        except Error as e:
            add_to_log("load_tables","DB error :"+e.msg)

def maininit(gui, *args, **kwargs):
    global w, top_level, rootor
    w = gui
    top_level = top
    root = top


def vp_start_gui():
    global w, root, top
    root = tk.Tk()
    top = MainWindow(root)
    maininit(root, top)
    root.mainloop()

class CustomerWindow(tk.Tk):
        def __init__(self, master):
            super().__init__()
            self.master=master
            tk.Frame.__init__(self.master)

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

        glb_active_product_frame_content = 0
        varfunc = self.employee_button_clicked
        self.add_frame_buttons(0, self.product_frame,glb_employees,glb_employees_page_count,varfunc)

    def customer_frame_def(self):
        global glb_active_served_customers
        global top
        global glb_active_product_frame_content
        glb_active_product_frame_content = 2
        get_served_customers()
        varfunc = self.customer_button_clicked
        self.add_frame_buttons(1, self.product_frame, glb_active_served_customers,glb_active_customers_page_count,varfunc)

    def call_back_customer_frame_def(self):
        global glb_customers_on_cashier
        global top
        global glb_active_product_frame_content
        font11 = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        glb_active_product_frame_content = 3
        get_customers_on_cashier()
        varfunc = self.call_back_customer_no_clicked
        self.add_frame_buttons(0, self.product_frame,glb_customers_on_cashier,glb_callback_customers_page_count,varfunc)

    def display_frame_def(self):
        global top
        global root

        self.display_frame.place(relx=0.0, rely=0.0, relheight=0.100, relwidth=0.994)
        self.product_frame.configure(width=795)
        self.customer_no = tk.Text(self.display_frame, height=1, width=4, font=("Arial Bold", 25),
                                   bg='dark blue', fg="white")
        self.scale_display = tk.Text(self.display_frame, height=1, width=10, font=("Arial Bold", 25),
                                     bg='dark green', fg="white")
        self.scale_type = tk.Text(self.display_frame, height=1, width=3, font=("Arial Bold", 25),
                                  bg='dark green', fg="white")
        self.prdct_barcode = tk.Text(self.display_frame, height=1, width=2, font=('Arial Bold', 25))
        self.employee_text = tk.Text(self.display_frame, height=1, width=20, font=("Arial Bold", 25))
        self.scale_type.insert(END, "Kg")
        self.customer_no.insert(END, "0")
        self.employee_text.insert(END,"")
        reyon_names = []
        for index, reyonObj in enumerate(glb_reyonlar):
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
        self.employee_text.grid(row=0,column=5)
        self.prdct_barcode.focus_set()
        self.prdct_barcode.bind('<Key-Return>', self.read_barcode)

    def read_barcode(self, event):
        global glb_sales
        global root
        root.config(cursor="watch")
        root.update()
        textdata = self.prdct_barcode.get('1.0', END)
        textdata = textdata.rstrip("\n")
        textdata = textdata.lstrip("\n")
        self.prdct_barcode.delete('1.0', END)
        salesObj = Sales()
        if get_product_based_on_barcod(textdata, salesObj):
            glb_sales.append(salesObj)
        self.update_products_sold()
        self.update_products_sold_for_customer()
        root.config(cursor="")


    def add_frame_buttons(self, active_served_customers, frame, btn_list, page_count, func):
        global glb_screensize
        if glb_screensize == 800:
            buttonwidth=19
            buttonheight=2
            row_size, col_size = 4, 2
            btn_font = "-family {Segoe UI} -size 12 -weight bold -slant " \
                     "roman -underline 0 -overstrike 0"
        else:
            buttonwidth=24
            buttonheight=2
            row_size, col_size = 5, 2
            btn_font = "-family {Segoe UI} -size 16 -weight bold -slant " \
                     "roman -underline 0 -overstrike 0"

        for child in frame.winfo_children():  # Clear frame contents whatever it is
            child.destroy()
        lower_cnt = page_count * row_size * col_size  # calculate lower bound in the btn_list
        while lower_cnt > len(btn_list):  # if lower bound is more than list size adjust it
            page_count = page_count - 1
            lower_cnt = page_count * row_size * col_size
        upper_cnt = lower_cnt + row_size * col_size  # calculate upper bound in the list
        if upper_cnt > len(btn_list):  # if upper bound more than list size adjust it
            upper_cnt = len(btn_list)
        btn_no = 0
        while lower_cnt < upper_cnt:
            obj = btn_list[lower_cnt]
            button = tk.Button(frame, text=obj.Name)
            button.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
            button.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000")
            button.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", width=buttonwidth, height=buttonheight,
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
            button.configure(font=btn_font, foreground="#000000", highlightbackground="#d9d9d9", highlightcolor="black",
                             pady="0", width=buttonwidth, height=buttonheight)
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
        if glb_screensize==800:
            sum_font = "-family {Segoe UI} -size 8 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
            entry_products_font = "-family {Segoe UI} -size 8 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        else:
            sum_font = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
            entry_products_font = "-family {Segoe UI} -size 10 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        self.products_sold_frame.place(relx=0.0, rely=0.110, relheight=0.550, relwidth=0.350)
        self.products_sold_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9",
                                           highlightbackground="#d9d9d9")
        self.products_sold_frame.configure(highlightcolor="black", width=155)
        self.entry_products = tk.Text(self.products_sold_frame)
        self.entry_products.place(relx=0.010, rely=0.02, relheight=0.84, relwidth=0.650)
        self.entry_products.configure(font=entry_products_font)
        self.entry_products.configure(takefocus="")
        self.entry_amount_sold=tk.Text(self.products_sold_frame)
        self.entry_amount_sold.tag_configure("right",justify=RIGHT)
        self.entry_amount_sold.tag_add("right",1.0,"end")
        self.entry_amount_sold.place(relx=0.650, rely=0.02, relheight=0.84, relwidth=0.160)
        self.entry_amount_sold.configure(font=entry_products_font, takefocus="")

        self.entry_calculatedtotal = tk.Text(self.products_sold_frame)
        self.entry_calculatedtotal.tag_configure("right",justify=RIGHT)
        self.entry_calculatedtotal.tag_add("right",1.0,"end")
        self.entry_calculatedtotal.place(relx=0.810, rely=0.02, relheight=0.84, relwidth=0.170)
        self.entry_calculatedtotal.configure(font=entry_products_font, takefocus="")
        self.label_sum = tk.Label(self.products_sold_frame)
        self.label_sum.place(relx=0.040, rely=0.88, relheight=0.10, relwidth=0.300)
        # self.label_sum.configure(background="#d9d9d9")
        self.label_sum.configure(disabledforeground="#a3a3a3")
        self.label_sum.configure(font=sum_font)
        self.label_sum.configure(foreground="#000000")
        self.label_sum.configure(text='''Toplam''')
        self.entry_sum = tk.Text(self.products_sold_frame, height=1, width=80, font=sum_font)
        self.entry_sum.tag_configure("right",justify=RIGHT)
        self.entry_sum.tag_add("right",1.0,"end")
        self.entry_sum.place(relx=0.790, rely=0.88, relheight=0.10, relwidth=0.190)

    def functions_frame_def(self):
        global top
        global glb_screensize
        if glb_screensize==800:
            buttons_height = 38
            buttons_width = 180
            btn_font = "-family {Segoe UI} -size 12 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"
        else:
            buttons_height = 65
            buttons_width = 250
            btn_font = "-family {Segoe UI} -size 15 -weight bold -slant " \
                 "roman -underline 0 -overstrike 0"

        self.functions_frame.place(relx=0.0, rely=0.700, relheight=0.200, relwidth=0.994)
        self.functions_frame.configure(relief='groove', borderwidth="2", background="#d9d9d9")
        self.functions_frame.configure(highlightbackground="#f0f0f0", width=795)
        self.btn_dara = tk.Button(self.functions_frame)
        self.btn_dara.configure(command=lambda btn=self.btn_dara: self.btn_dara_clicked())
        self.btn_dara.place(relx=0.013, rely=0.050, height=buttons_height, width=buttons_width)
        self.btn_dara.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_dara.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000")
        self.btn_dara.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0", text='''Dara''',
                                width=20)

        self.btn_changeuser = tk.Button(self.functions_frame)
        self.btn_changeuser.configure(command=lambda btn=self.btn_changeuser: self.btn_change_user_clicked())
        self.btn_changeuser.place(relx=0.264, rely=0.050, height=buttons_height, width=buttons_width)
        self.btn_changeuser.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_changeuser.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000")
        self.btn_changeuser.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                      text='''Çalışan Değiştir''', width=20)

        self.btn_call_back_customer = tk.Button(self.functions_frame)
        self.btn_call_back_customer.configure(
            command=lambda btn=self.btn_call_back_customer: self.call_back_customer_clicked())
        self.btn_call_back_customer.place(relx=0.516, rely=0.050, height=buttons_height, width=buttons_width)
        self.btn_call_back_customer.configure(activebackground="#ececec", activeforeground="#000000",
                                              background="#d9d9d9")
        self.btn_call_back_customer.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000")
        self.btn_call_back_customer.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                              text='''Müşteri Geri Çağır''', width=20)

        self.btn_cancelsale = tk.Button(self.functions_frame)
        self.btn_cancelsale.configure(command=lambda btn=self.btn_cancelsale: self.btn_cancelsale_clicked())
        self.btn_cancelsale.place(relx=0.767, rely=0.050, height=buttons_height, width=buttons_width)
        self.btn_cancelsale.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_cancelsale.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000")
        self.btn_cancelsale.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                      text='''Satışı İptal Et''', width=20)

        self.btn_cleardara = tk.Button(self.functions_frame)
        self.btn_cleardara.configure(command=lambda btn=self.btn_cleardara: self.btn_cleardara_clicked())
        self.btn_cleardara.place(relx=0.013, rely=0.500, height=buttons_height, width=buttons_width)
        self.btn_cleardara.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_cleardara.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000",
                                     text='''Darayı Temizle''', width=20)

        self.btn_savesale = tk.Button(self.functions_frame)
        self.btn_savesale.configure(command=lambda btn=self.btn_savesale: self.btn_savesale_clicked())
        self.btn_savesale.place(relx=0.264, rely=0.500, height=buttons_height, width=buttons_width)
        self.btn_savesale.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_savesale.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000",
                                    text='''Satışı Kaydet''', width=20)

        self.btn_sendcashier = tk.Button(self.functions_frame)
        self.btn_sendcashier.configure(command=lambda btn=self.btn_sendcashier: self.btn_send_cashier_clicked())
        self.btn_sendcashier.place(relx=0.516, rely=0.500, height=buttons_height, width=buttons_width)
        self.btn_sendcashier.configure(activebackground="#ececec", activeforeground="#000000", background="#d9d9d9")
        self.btn_sendcashier.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000")
        self.btn_sendcashier.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                       text='''Kasaya Gönder''', width=20)

        self.btn_clearlasttransaction = tk.Button(self.functions_frame)
        self.btn_clearlasttransaction.configure(
            command=lambda btn=self.btn_clearlasttransaction: self.btn_clearlasttransaction_clicked())
        self.btn_clearlasttransaction.place(relx=0.767, rely=0.500, height=buttons_height, width=buttons_width)
        self.btn_clearlasttransaction.configure(activebackground="#ececec", activeforeground="#000000",
                                                background="#d9d9d9")
        self.btn_clearlasttransaction.configure(disabledforeground="#a3a3a3", font=btn_font, foreground="#000000")
        self.btn_clearlasttransaction.configure(highlightbackground="#d9d9d9", highlightcolor="black", pady="0",
                                                text='''Son İşlemi Sil''', width=20)


    def next_product_button_clicked(self):
        global glb_product_page_count
        global glb_callback_customers_page_count
        global glb_active_customers_page_count
        global glb_employees_page_count
        global glb_active_product_frame_content
        global root

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
        global root

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
        global root

        root.config(cursor="watch")
        root.update()
        glb_customer_no = btn.cget("text")
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        sales_load(glb_customer_no, -1)
        self.product_frame_def()
        self.update_products_sold()
        self.update_products_sold_for_customer()
        root.config(cursor="")

    def btn_send_cashier_clicked(self):
        global glb_customer_no
        global glb_sales_line_id
        global root

        root.config(cursor="watch")
        root.update()
        sales_hard_delete(glb_customer_no)
        sales_save(0)
        glb_sales.clear()
        self.update_products_sold()
        self.update_products_sold_for_customer()
        glb_customer_no = 0
        glb_sales_line_id = 1
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, "0")
        try:
            resp = requests.get("http://"+glb_webHost+"/api/DataRefresh")
        except Error as e:
            add_to_log("sendToCahsier","SignalRErr :"+e.msg)
        self.btn_cleardara_clicked()
        self.new_customer_clicked()
        root.config(cursor="")

    def btn_change_user_clicked(self):
        global top
        global glb_employees_selected
        global glb_customer_no
        global root

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
        global root

        root.config(cursor="watch")
        root.update()
        salesID = btn.cget("text")
        glb_sales.clear()
        sales_load(salesID, 0)
        sales_update( 0, -1)
        self.customer_no.delete('1.0', END)
        self.customer_no.insert(END, glb_customer_no)
        self.update_products_sold()
        self.update_products_sold_for_customer()
        self.product_frame_def()
        resp = requests.get("http://"+glb_webHost+"/api/DataRefresh")
        root.config(cursor="")

    def call_back_customer_clicked(self):
        global root

        root.config(cursor="watch")
        root.update()
        self.call_back_customer_frame_def()
        root.config(cursor="")

    def new_customer_clicked(self):
        global top
        global glb_sales_line_id
        global glb_employees_selected
        global glb_customer_no
        global root

        root.config(cursor="watch")
        root.update()
        self.message_box_text.delete("1.0", END)
        glb_sales.clear()
        salescounterobj = SalesCounter()
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
        global root

        root.config(cursor="watch")
        root.update()
        sales_hard_delete(glb_customer_no)
        sales_save(-2)
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
        global glb_customer_no
        global root

        root.config(cursor="watch")
        root.update()
        sales_hard_delete(glb_customer_no)
        sales_save(-1)
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
        global root

        root.config(cursor="watch")
        root.update()
        glb_base_weight = glb_base_weight + float(self.scale_display.get("1.0", END).strip("\n"))
        self.scale_display.delete("1.0", END)
        self.scale_display.insert(END, "0.000".rjust(20))
        root.config(cursor="")

    def btn_cleardara_clicked(self):
        global glb_base_weight
        global root
        global glb_filter_data

        root.config(cursor="watch")
        root.update()
        glb_base_weight = 0
        floatval = float(glb_filter_data) - glb_base_weight
        mydata = "{:10.3f}".format(floatval)
        mydata = mydata.rjust(20)
        self.scale_display.delete("1.0", END)
        self.scale_display.insert(END, mydata)
        root.config(cursor="")

    def btn_clearlasttransaction_clicked(self):
        global glb_sales_line_id
        global root

        root.config(cursor="watch")
        root.update()
        if len(glb_sales) > 0:
            glb_sales.pop(-1)
            glb_sales_line_id = glb_sales_line_id -1
            self.update_products_sold()
            self.update_products_sold_for_customer()
        root.config(cursor="")

    def checkreyon(self, event: object):
        global glb_scaleId
        global glb_employees_selected
        global root

        root.config(cursor="watch")
        root.update()
        self.message_box_text.delete("1.0", END)
        if glb_employees_selected != "":
            tt = self.select_reyon.get()
            glb_scaleId = self.select_reyon.current()
            teraziID = [x.teraziID for x in glb_reyonlar if x.ReyonName == tt][0]
            load_products(teraziID)
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
        global root

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
            teraziID = [x.teraziID for x in glb_reyonlar if x.ReyonName == tt][0]
            load_products(teraziID)
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
            self.employee_text.delete('1.0', END)
            self.employee_text.tag_configure('right',justify='right')
            self.employee_text.insert(END,glb_employees_selected,'right')
            self.prdct_barcode.focus_set()
        else:
            self.message_box_text.insert(END, "Reyon Seçimini Yapmadan Personel Seçimi Yapılamaz")
        root.config(cursor="")

    def update_products_sold(self):
        self.entry_products.delete("1.0", END)
        self.entry_amount_sold.delete("1.0",END)
        self.entry_calculatedtotal.delete("1.0", END)
        sum_calculated_price = 0
        for salesObj in glb_sales:
            self.entry_products.insert(END, " "+salesObj.Name + "\n")
            strAmount="{:.3f}\n".format(salesObj.amount).rjust(6, ' ')
            self.entry_amount_sold.insert(END,strAmount,"right")
            calculated_price = float(salesObj.amount * float(salesObj.retailPrice))
            sum_calculated_price = sum_calculated_price + calculated_price
            myData = "{:.2f}\n".format(calculated_price).rjust(8, ' ')
            self.entry_calculatedtotal.insert(END, myData,"right")
        self.entry_sum.delete("1.0", END)
        self.entry_sum.insert(END, "{:5.2f}".format(sum_calculated_price).rjust(8, ' '),"right")

    def update_products_sold_for_customer(self):
        self.cust_window.products_sold.delete("1.0", END)
        self.cust_window.products_sold_amount.delete("1.0", END)
        self.cust_window.products_sold_price.delete("1.0", END)
        sum_calculated_price = 0
        for salesObj in glb_sales:
            self.cust_window.products_sold.insert(END, salesObj.Name + "\n")
            self.cust_window.products_sold_amount.insert(END, "{:.3f}\n".format(salesObj.amount).rjust(8, ' '), "right")
            calculated_price = float(salesObj.amount * float(salesObj.retailPrice))
            sum_calculated_price = sum_calculated_price + calculated_price
            myData = "{:.2f}\n".format(calculated_price).rjust(8, ' ')
            self.cust_window.products_sold_price.insert(END, myData, "right")
        self.cust_window.products_sold_total.delete("1.0", END)
        self.cust_window.products_sold_total.insert(END, "{:.2f}".format(sum_calculated_price).rjust(8, ' '), "right")

    def product_button_clicked(self, btn):
        global glb_sales_line_id
        global glb_employees_selected
        global glb_customer_no
        global glb_filter_data

        if (glb_customer_no != 0):
            salesObj = Sales()
            salesObj.Name = btn.cget("text")
            salesObj.salesID = glb_customer_no
            salesObj.salesLineID = glb_sales_line_id
            glb_sales_line_id = glb_sales_line_id + 1
            salesObj.personelID = [x.personelID for x in glb_employees if x.Name == glb_employees_selected][0]
            salesObj.productBarcodeID=[x.productBarcodeID for x in glb_product_names if x.Name == salesObj.Name][0]
            """if productBarcodeID is 9999 then amount becomes 1. this is used for products where barcode ID does not exists and price does not depend on weight"""
            amountTxt=""
            if salesObj.productBarcodeID == "9999":
                amountTxt="1.0"
            else:
                amountTxt = self.scale_display.get("1.0", END).strip("\n")
                glb_filter_data=amountTxt
            if len(amountTxt) > 0:
                salesObj.amount = float(amountTxt)
            else:
                self.message_box_text.insert(END, "Miktar bilgisi hatalı")
                return
            salesObj.retailPrice = [x.price for x in glb_product_names if x.Name == salesObj.Name][0]
            salesObj.productID = [x.productID for x in glb_product_names if x.Name == salesObj.Name][0]
            salesObj.typeOfCollection = 0
            glb_sales.append(salesObj)
            self.update_products_sold()
            self.update_products_sold_for_customer()
        else:
            self.message_box_text.insert(END, "Yeni Müşteri Seçilmeden Ürün Seçimi Yapılamaz")

    def __init__(self, top=None):
        super().__init__()
        global glb_screensize
        global glb_serial_object
        glb_screensize=top.winfo_screenwidth()
        w, h = top.winfo_screenwidth()/2, root.winfo_screenheight()
        top.geometry("%dx%d+0+0" % (w, h))
        top.attributes("-fullscreen", FALSE)
        # top.geometry("800x480+1571+152")
        top.title("Terazi Ara Yüzü")
        top.configure(background="#d9d9d9")
        """Create frames"""
        self.master=top
        self.display_frame = tk.Frame(top)
        self.products_sold_frame = tk.Frame(top)
        self.product_frame = tk.Frame(top)
        self.paging_frame = tk.Frame(top)
        self.functions_frame = tk.Frame(top)
        self.message_box_frame = tk.Frame(top)
        self.message_box_frame_def()
        load_tables()
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
        """"Customer view window definition """
        self.cust_window = tk.Toplevel(self.master)
        self.cust_window.geometry("%dx%d+1200+0" % (w, h))
        self.cust_window.attributes("-fullscreen", True)
        self.cust_window.title("Müşteri Bilgi Ekranı")
        customer_window_def(self.cust_window)
        res = 0
        if glb_data_entry == 0:
            if glb_windows_env:
                res=connect(self, 1, 9600, '5')
            else:
                res=connect(self, 2, 9600, 'USB0')
                if res==0:
                    res=connect(self, 2, 9600, 'USB1')
        if res == 1:
            t1 = threading.Thread(target=get_data,
                                      args=(self, self.scale_display,))
            t1.daemon = True
            t1.start()

def customer_window_def(CustomerWindow):
        font18 = "-family {Segoe UI} -size 18 -slant " \
                 "roman -underline 0 -overstrike 0"
        font9 = "-family {Segoe UI} -size 11 -weight bold -slant roman" \
                " -underline 0 -overstrike 0"

        CustomerWindow.company_label = tk.Label(CustomerWindow, height=1, width=30, font=font18)
        CustomerWindow.company_label.place(relx=0.40, rely=0.0, relheight=0.05, relwidth=0.200)
        CustomerWindow.company_label.config(text='''G Ü L S E V EN''', fg='dark red')
        CustomerWindow.products_sold_label = tk.Label(CustomerWindow, height=1, width=30, font=font18)
        CustomerWindow.products_sold_label.place(relx=0.010, rely=0.05, relheight=0.1, relwidth=0.700)
        CustomerWindow.products_sold_label.config(text=''' Ürün''', anchor=W, bg='dark red', fg='white')
        CustomerWindow.products_sold = tk.Text(CustomerWindow, height=2, width=30)
        CustomerWindow.products_sold.place(relx=0.010, rely=0.16, relheight=0.70, relwidth=0.700)
        CustomerWindow.products_sold.configure(font=font18)
        CustomerWindow.products_sold.configure(takefocus="")
        CustomerWindow.products_sold_amount_label = tk.Label(CustomerWindow, height=1, width=30, font=font18)
        CustomerWindow.products_sold_amount_label.place(relx=0.720, rely=0.05, relheight=0.1, relwidth=0.10)
        CustomerWindow.products_sold_amount_label.config(text='''Miktar ''', anchor=E, bg='dark red', fg='white')
        CustomerWindow.products_sold_amount = tk.Text(CustomerWindow, height=2, width=10)
        CustomerWindow.products_sold_amount.tag_configure("right", justify=RIGHT)
        CustomerWindow.products_sold_amount.tag_add("right", 1.0, "end")
        CustomerWindow.products_sold_amount.place(relx=0.720, rely=0.16, relheight=0.70, relwidth=0.10)
        CustomerWindow.products_sold_amount.configure(font=font18)
        CustomerWindow.products_sold_price_label = tk.Label(CustomerWindow, height=1, width=30, font=font18)
        CustomerWindow.products_sold_price_label.place(relx=0.830, rely=0.05, relheight=0.1, relwidth=0.15)
        CustomerWindow.products_sold_price_label.config(text='''Tutar ''', anchor=E, bg='dark red', fg='white')
        CustomerWindow.products_sold_price = tk.Text(CustomerWindow, height=2, width=10)
        CustomerWindow.products_sold_price.tag_configure("right", justify=RIGHT)
        CustomerWindow.products_sold_price.tag_add("right", 1.0, "end")
        CustomerWindow.products_sold_price.place(relx=0.830, rely=0.16, relheight=0.70, relwidth=0.15)
        CustomerWindow.products_sold_price.configure(font=font18)
        CustomerWindow.products_sold_total_label = tk.Label(CustomerWindow, height=1, width=30, font=font18)
        CustomerWindow.products_sold_total_label.place(relx=0.720, rely=0.87, relheight=0.1, relwidth=0.10)
        CustomerWindow.products_sold_total_label.config(text=''' TOPLAM ''', anchor=NW, bg='dark red', fg='white')
        CustomerWindow.products_sold_total = tk.Text(CustomerWindow, height=2, width=10)
        CustomerWindow.products_sold_total.tag_configure("right", justify=RIGHT)
        CustomerWindow.products_sold_total.tag_add("right", 1.0, "end")
        CustomerWindow.products_sold_total.place(relx=0.830, rely=0.87, relheight=0.10, relwidth=0.15)
        CustomerWindow.products_sold_total.configure(font=font18, bg='dark red', fg='white')

def connect(self, env, baud, port):
    global glb_serial_object

    try:
        if env == 2:
            glb_serial_object = serial.Serial(port='/dev/tty' + str(port), baudrate=baud)
        elif env == 1:
            glb_serial_object = serial.Serial('COM' + str(port), baud)
    except serial.SerialException as msg:
        if env == 2 or port == 'USB1':
            """if windows give message. If linux and tested for USB1 then error else USB0 then test for USB1
            """
            messagebox.showinfo("Hata Mesajı", "Terazi ile Bağlantı kurulamadı. Terazinin açık ve bağlı olduğunu kontrol edip tekrar başlatın.")
        add_to_log("Connect", "Seri Port Hatası")
        return 0
    return 1

def get_data(self, scale_display):
    """This function serves the purpose of collecting data from the serial object and storing
    the filtered data into a global variable.

    The function has been put into a thread since the serial event is a blocking function.
    """
    global glb_serial_object
    global glb_filter_data
    glb_filter_data = ""
    while (1):
        try:
            serial_data = str(glb_serial_object.readline(), 'utf-8')
            serial_data = serial_data.rstrip('\r')
            serial_data = serial_data.rstrip('\n')
            if (serial_data[0:1] == '+') and (serial_data.find("kg",1,len(serial_data))):
                if (glb_filter_data != serial_data[2:serial_data.index("kg")]):
                   glb_filter_data = serial_data[2:serial_data.index("kg")]
                   scale_display.delete(1.0, END)
                   floatval = float(glb_filter_data) - glb_base_weight
                   mydata = "{:10.3f}".format(floatval)
                   mydata = mydata.rjust(13)
                   scale_display.insert(END, mydata)
                   add_to_log("SeriFilter", "#" + glb_filter_data + "#")
                   print(glb_filter_data)
                else:
                   pass
            else:
                pass
        except NameError as err:
            add_to_log("Get data", err)
            pass
        except TypeError as err:
            add_to_log("Get data", err)
            pass
        except UnicodeDecodeError:
            pass

def getopts(argv):
   opts = {}
   while argv:
      if argv[0][0] == '-': # find "-name value" pairs
         opts[argv[0]] = argv[1] # dict key is "-name" arg
         argv = argv[2:]
      else:
         argv = argv[1:]
   return opts

if __name__ == '__main__':
    from sys import argv  # example client code
    myargs = getopts(argv)
    glb_data_entry=0
    if ("-dataentry" in myargs.keys() ):
        glb_data_entry=myargs["-dataentry"]
    if ("-location" in myargs.keys()):
        glb_locationid = myargs["-location"]
        vp_start_gui()

