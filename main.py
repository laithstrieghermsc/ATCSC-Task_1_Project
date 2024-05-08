import json
import threading
from datetime import datetime

import web
from shared import DataHandler

# initialize globals
products = {}
members = []
records = []


def unpack(filename: str):
    """load json save data in file"""
    with open(filename) as f_in:
        return json.load(f_in)


def convert_values_to_int(dictionary):
    """search for strings that can be converted to int"""
    for key, value in dictionary.items():
        try:
            dictionary[key] = int(value[0])
        except ValueError:
            dictionary[key] = True if dictionary[key][0] == "yes" else False


def get_cost(name):
    """got the price of a pizza named 'name'"""
    global products
    for _ in products["menu"]:
        if _["id"] == name:
            return _["price"]


def is_today(given_epoch):
    """Determine if a time of a given epoch is in the same UTC+0800 'day'"""
    return datetime.fromtimestamp(given_epoch).date() == datetime.now().date()


def get_daily_total():
    """get totals for the day"""
    global records
    m = 0  # monetary total
    d = 0  # deliveries total
    t = 0  # taxes total
    for _ in records:
        if is_today(_.get("time")):  # if an order was made today
            m += _.get("subtotal")  # this is actually total profit as it is not including tax.
            if _.get("delivery"):
                d += 1  # add delivery
            t = m * 0.1  # tax

    return m, d, t  # return tuple


def get_pizza_total_daily(pizza):
    """find total count and profit from pizza 'pizza'"""
    global products, records
    price = 0
    count = 0
    for _ in products.get("menu"):
        if _.get("id") == pizza:
            price = _.get("price")  # find price of pizza
            break  # stop searching if found
    for _ in records:  # count pizzas
        if is_today(_.get("time")):
            count += _.get("order").get(pizza)
    return count, count * price


def get_pizzas_daily():
    """create html list string for pizzas totals"""
    global products
    _ = ""
    for __ in products.get("menu"):  # search menu
        ___ = __.get("id")
        count, total = get_pizza_total_daily(___)
        _ += f"<li>{___}: {count}, ${round(total, 2)}</li>"
    return _


def metrics():
    """create a dictionary for web.AdminHandler to interpret metrics"""
    global records
    total_money, deliveries, tax = get_daily_total()
    return {
        "records": records,
        "total": round(total_money, 2),
        "pizzas": get_pizzas_daily(),
        "deliveries": deliveries,
        "tax": round(tax, 2)
    }


def ping(value: threading.Thread):
    """object communication test"""
    print(f"Ping from '%s'" % value.name)
    return "Pong from '%s'" % __name__


def process_order(order):
    """process an order based on raw query values"""

    global records, members
    # convert int values to correct type (i.e. remove from list)
    convert_values_to_int(order)

    # default
    member = None
    if order.get("membership_number") is not None:
        member = order.pop("membership_number")  # if provided get Member number and remove from list
    if order.get("delivery") is not None:
        delivery = order.pop("delivery")  # if provided, HTML POST requests do not send responses for unchecked -
        # boxes by default, so, get boolean and remove from list
    else:
        delivery = False
    # removes not product (pizzas) values

    subtotal = 0.00
    for key, value in order.items():  # remaining items should all be pizzas
        subtotal += get_cost(key) * value  # add pizza costs

    # get final price information
    total, price_quotient = adjust_price_quotient(delivery, member, subtotal)

    # create a record using information from handler
    record = {
        "member-id": member if member in members else None,
        "order": order,
        "delivery": delivery,
        "subtotal": round(subtotal, 2),
        "discount": round(1 - price_quotient, 2),
        "total": round(total, 2),
        "time": int(datetime.now().timestamp())
    }

    records.append(record)  # add record
    with open('data/order_logs.json', 'w', encoding='utf-8') as _:  # save logs
        json.dump({"orders": records}, _, ensure_ascii=False, indent=4)


def adjust_price_quotient(delivery: bool, member: bool, price: float):
    """create final price from subtotal add delivery, tax, and apply $100 and membership discounts"""
    sub_total = price  # get local copy
    quotient = 1.00  # 100%
    sub_total += 8 if delivery else 0  # add delivery fee if applicable.
    quotient -= 0.05 if member in members else 0  # -5% if member
    quotient -= 0.05 if sub_total > 100 else 0  # -5% if over $100
    sub_total *= quotient  # apply to price
    final_price = sub_total * 1.1  # 10% tax

    return final_price, quotient  # keep quotient for logs


if __name__ == "__main__":

    # collect save data
    records = unpack("data/order_logs.json").get("orders")
    products = unpack("data/products.json")
    members = unpack("data/members.json").get("members")

    # create a globally accessible object storage system
    handler = DataHandler(products, metrics, ping)

    # initialise and start website, pass handler for accessibility
    website = web.Web(handler)
    httpd = threading.Thread(name="__http_daemon__", target=website.listen, args=())
    httpd.start()

    # search for data from WebHandler in data handler
    while True:
        if handler.available:
            # get semi-raw query values and process the order
            process_order(handler.get_order())
