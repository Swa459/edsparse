# EDSParse

A Python parser for `.eds` (**Evaluable Data Set**) files.  
Smarter than JSON. Expressions built-in. Cleaner to write.

---

## What is EDS?

EDS is a modern data exchange format designed to be lightweight and expressive.  
Unlike JSON, EDS supports **inline math expressions**, **comments**, **optional quotes**, and a clean group-based structure.

```
# shop.eds

Product:
    name = "Wireless Headphones"
    basePrice = 2500
    taxRate = 0.18
    finalPrice = arth(basePrice * (1 + taxRate))
    tags = ['electronics', 'audio', 'wireless']
    inStock = true
    discount = null
```

---

## Installation & Uninstallation

___Install:___
```bash
pip install edsparse
```

___Unistall:___
```bash
pip install -y edsparse
```

---

## Quick Start

```python
import edsparse

eds = edsparse.Open("shop.eds")

product = eds.ReadData("Product")
print(product["name"])        # Wireless Headphones
print(product["finalPrice"])  # 2950.0
print(product["tags"])        # ['electronics', 'audio', 'wireless']
```

---

## EDS Syntax

### Groups
A group is the core structure in EDS — like a class in Python or an object in JSON.

```
Product:
    name = "Wireless Headphones"
    basePrice = 2500
```

### Fields
Fields are defined as `key = value` pairs inside a group.

```
name = "Swastik"
age = 10
score = 99.5
active = true
nickname = null
```

### Expressions — `arth()`
Use `arth()` to write math expressions that reference other fields in the same group.

```
price = 1000
taxRate = 0.18
tax = arth(price * taxRate)
total = arth(price + tax)
```

> **Note:** Only values wrapped in `arth()` are evaluated. Everything else is treated as plain data.

### Lists
```
tags = ['electronics', 'audio', 'wireless']
scores = [99, 87, 95]
```

### Comments
```
# This is a comment
name = "Swastik"  # This is an inline comment
```

### Supported Types
| Type | Example |
|---|---|
| String | `"Hello"` or `Hello` |
| Integer | `25` |
| Float | `3.14` |
| Boolean | `true` / `false` |
| Null | `null` |
| List | `[1, 2, 3]` |
| Expression | `arth(price * 0.18)` |

---

## API Reference

### File Setup
```python
eds = edsparse.Open("shop.eds")          # open existing file
eds = edsparse.CreateFile("new.eds")     # create new file
```

### Reading & Writing
```python
eds.WriteData("Product", {"name": "Headphones", "price": 2500})
eds.ReadData()                           # all groups
eds.ReadData("Product")                  # one group
eds.GroupToDict("Product")               # raw unevaluated fields
```

### Updating & Deleting
```python
eds.UpdateData("Product", "price", 3000)
eds.DeleteData("Product")
eds.ClearGroup("Product")                # keeps header, removes fields
```

### Group Utilities
```python
eds.GroupExists("Product")               # True / False
eds.ListGroups()                         # ['Product', 'Customer']
eds.CountGroups()                        # 3
eds.RenameGroup("Product", "Item")
eds.DuplicateGroup("Product", "ProductBackup")
```

### Search
```python
eds.SearchValue("Bengaluru")             # [('Customer', 'city')]
eds.SearchGroup("prod")                  # ['Product1', 'Product2']
```

### File Info
```python
eds.SizeOfFile()                         # bytes
eds.SizeOfGroup("Product")              # bytes of that group block
eds.GroupDatas("Product")               # number of fields in group
eds.FileStats()                          # full summary dict
```

### Merge, Export & Import
```python
edsparse.MergeFiles(['a.eds', 'b.eds'], 'merged.eds')
edsparse.ExportToJSON("shop.eds")        # creates shop.json
edsparse.ImportFromJSON("shop.json")     # creates shop.eds
edsparse.CompareFiles("v1.eds", "v2.eds")
```

### Batch Operations (Threaded ⚡)
```python
# Read multiple files at once
results = edsparse.BatchRead(['file1.eds', 'file2.eds'])

# Write to multiple files at once
edsparse.BatchWrite([
    {'file': 'shop.eds',  'group': 'Product', 'data': {'name': 'Headphones'}},
    {'file': 'users.eds', 'group': 'User1',   'data': {'name': 'Swastik'}},
])

# Delete from multiple files at once
edsparse.BatchDelete([
    {'file': 'shop.eds',  'group': 'OldProduct'},
    {'file': 'users.eds', 'group': 'InactiveUser'},
])
```

---

## Comparison with JSON

|  | EDS | JSON |
|---|---|---|
| Arithmetic | ✅ `arth()` | ❌ |
| Comments | ✅ | ❌ |
| Optional quotes | ✅ | ❌ |
| Readability | ✅ Clean | 🟡 Noisy |
| Ecosystem | 🌱 Growing | ✅ Massive |
| Language support | Python | Every language |

---

## License

Copyright (c) 2026 Swastik Bachhar — All rights reserved.  
See [LICENSE](./LICENSE) for details.
