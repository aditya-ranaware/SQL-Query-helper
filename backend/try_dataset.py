from app.services.dataset import DatasetError, from_csv_files, from_schema_text, sample_dataset


def expect_error(label, fn):
    try:
        fn()
        print(f"NO ERROR (bad)  {label}")
    except DatasetError as e:
        print(f"error ok        {label}: {e}")


print("1) CSV FILES")
customers = b"Customer ID,Full Name,City,Joined On,Spend\n1,Asha,Pune,2024-03-01,1200.50\n2,Ravi,Mumbai,2024-04-12,\n"
orders = "order id;customer;status\n1;1;shipped\n2;1;cancelled\n".encode()
d = from_csv_files([("Customers 2024.csv", customers), ("orders.csv", orders)])
for t in d.tables.values():
    print("  ", t.name, t.columns, "| rows:", len(t.rows))

print("\n2) PASTED CREATE TABLE")
d = from_schema_text("CREATE TABLE customers (id INT PRIMARY KEY, name VARCHAR(50), balance DECIMAL(10,2)) ENGINE=InnoDB;")
print("  ", {n: t.columns for n, t in d.tables.items()}, "| has data:", d.has_data)

print("\n3) TYPED SHORT LINES")
d = from_schema_text("customers: id, name, city\nproducts(id int, price decimal(10,2))")
print("  ", {n: t.columns for n, t in d.tables.items()})

print("\n4) THE SAMPLE SHOP")
s = sample_dataset()
print("  ", {n: len(t.rows) for n, t in s.tables.items()})

print("\n5) MISTAKES")
expect_error("empty text", lambda: from_schema_text("   "))
expect_error("a sentence", lambda: from_schema_text("I have some tables"))
expect_error("not a csv", lambda: from_csv_files([("notes.txt", b"hello")]))
expect_error("header only", lambda: from_csv_files([("a.csv", b"id,name\n")]))