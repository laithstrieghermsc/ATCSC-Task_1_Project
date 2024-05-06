import json
import threading
import time

import web
# import sql
from shared import DataHandler

products = {}
members = []
records = []


def unpack(filename: str):
    with open(filename) as f_in:
        return json.load(f_in)


def convert_values_to_int(dictionary):
    for key, value in dictionary.items():
        try:
            dictionary[key] = int(value[0])
        except ValueError:
            dictionary[key] = True if dictionary[key] == "yes" else False


def get_cost(name):
    for _ in products["menu"]:
        if _["id"] == name:
            return _["price"]


def retrieve(pizza):
    return int(pizza[0]) if (
            len(pizza) == 1 and (pizza[0]).isdigit()) else None


def is_today(given_epoch):
    current_epoch = int(time.time())
    return (current_epoch + 3600 * 8) // 86400 == (given_epoch + 3600 * 8) // 86400  # 86400 seconds in a day


def get_daily_total():
    m = 0
    d = 0
    t = 0
    for _ in records:
        if is_today(_.get("time")):
            m += _.get("subtotal")  # this is actually total profit as it is not including tax.
            if _.get("delivery"):
                d += 1
            t = m * 0.1

    return m, d, t


def get_pizza_total_daily(pizza):
    price = 0
    count = 0
    for _ in products.get("menu"):
        if _.get("id") == pizza:
            price = _.get("price")
            break
    for _ in records:
        if is_today(_.get("time")):
            count += _.get("order").get(pizza)
    return count, count * price


def get_pizzas_daily():
    str = ""
    for _ in products.get("menu"):
        id = _.get("id")
        count, total = get_pizza_total_daily(id)
        str += f"<li>{id}: {count}, ${round(total, 2)}</li>"
    return str


def metrics():
    totalmoney, deliveries, tax = get_daily_total()
    return {
        "records": records,
        "total": round(totalmoney, 2),
        "pizzas": get_pizzas_daily(),
        "deliveries": deliveries,
        "tax": round(tax, 2)
    }


if __name__ == "__main__":
    records = unpack("data/orderlog.json").get("orders")
    products = unpack("data/products.json")
    members = unpack("data/members.json").get("members")
    handler = DataHandler("Success", products, metrics)
    wsite = web.Web(handler)
    daemon = threading.Thread(name="http_daemon", target=wsite.begin_listen, args=())
    daemon.start()

    while True:
        if handler.available:
            subtotal = 0.00
            price_quotient = 1.00
            order = handler.get_order()
            convert_values_to_int(order)
            member = None
            if order.get("memno") is not None:
                member = order.pop("memno")
            if order.get("deliv") is not None:
                delivery = order.pop("deliv")
            else:
                delivery = False

            for key, value in order.items():
                subtotal += get_cost(key) * value

            subtotal += 8 if delivery else 0
            price_quotient -= 0.05 if member in members else 0
            price_quotient -= 0.05 if subtotal > 100 else 0
            subtotal *= price_quotient
            total = subtotal * 1.1
            record = {
                "member-id": member if member in members else None,
                "order": order,
                "delivery": True,
                "subtotal": round(subtotal, 2),
                "discount": round(1 - price_quotient, 2),
                "total": round(total, 2),
                "time": int(time.time())
            }
            records.append(record)
            with open('data/orderlog.json', 'w', encoding='utf-8') as f:
                json.dump({"orders": records}, f, ensure_ascii=False, indent=4)
