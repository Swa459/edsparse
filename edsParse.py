from pathlib import Path
import threading
import json
import os

class Open:
    '''
    Thank you for using EDS and edsParser for your project. This module helps you to initialize
    the file, means, you need not mention the file's directory again and again in every function.
    If you want to send any feedback you might use the Feedback module.
    '''
    def __init__(self, filePath):
        if isinstance(filePath, str):
            p = Path(filePath)
            if p.exists() and p.suffix.lower() == ".eds":
                self.Path = filePath
            elif p.exists() and p.suffix.lower() != ".eds":
                print(f"eds.FileFormatError: This is not an eds file, this seems to be a/an {p.suffix} file.")
                exit(1)
            elif not p.exists():
                print("eds.FileExistsError: This file path seems to be incorrect, if you think it is correct,")
                print("                     Please check with the spellings.")
                exit(1)
        else:
            print("eds.FilePathDataTypeError: This doesn't seem to be a valid filePath, a filePath should be like:")
            print("                           'path/to/demoFile.eds'")
            exit(1)

    # ─────────────────────────────────────────────
    #  WRITE
    # ─────────────────────────────────────────────

    def WriteData(self, group, datas):
        '''
        Writes a group and its data to the .eds file.
        If the group already exists, it will be updated.
        If it doesn't exist, it will be appended.

        Parameters:
            group (str)  : The group name.
            datas (dict) : A dictionary of key-value pairs to write.

        Example:
            eds.WriteData("Product", {
                "name": "Wireless Headphones",
                "basePrice": 2500,
                "taxRate": 0.18,
                "finalPrice": "arth(basePrice * (1 + taxRate))"
            })
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        if not isinstance(datas, dict):
            print("eds.DataTypeError: Data must be a dictionary.")
            exit(1)

        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        newBlock = self._buildBlock(group, datas)

        if self._groupExists(content, group):
            content = self._replaceBlock(content, group, newBlock)
        else:
            content = content.rstrip() + "\n\n" + newBlock + "\n"

        with open(self.Path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _buildBlock(self, group, datas):
        '''Builds a group block string from a dict.'''
        lines = [f"{group}:"]
        for key, value in datas.items():
            if isinstance(value, str):
                if value.startswith("arth(") and value.endswith(")"):
                    lines.append(f"    {key} = {value}")
                else:
                    lines.append(f"    {key} = \"{value}\"")
            elif isinstance(value, list):
                inner = ', '.join(
                    f"'{item}'" if isinstance(item, str) else str(item)
                    for item in value
                )
                lines.append(f"    {key} = [{inner}]")
            elif value is None:
                lines.append(f"    {key} = null")
            elif isinstance(value, bool):
                lines.append(f"    {key} = {str(value).lower()}")
            else:
                lines.append(f"    {key} = {value}")
        return "\n".join(lines)

    def _groupExists(self, content, group):
        '''Checks if a group already exists in the file.'''
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith(group) and stripped.endswith(":"):
                return True
        return False

    def _replaceBlock(self, content, group, newBlock):
        '''Replaces an existing group block with a new one.'''
        lines = content.splitlines()
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith(group) and stripped.endswith(":"):
                result.append(newBlock)
                i += 1
                while i < len(lines):
                    nextLine = lines[i]
                    if nextLine.startswith("    ") or nextLine.strip() == "":
                        i += 1
                    else:
                        break
            else:
                result.append(line)
                i += 1
        return "\n".join(result)

    # ─────────────────────────────────────────────
    #  READ
    # ─────────────────────────────────────────────

    def ReadData(self, group=None):
        '''
        Reads and parses the .eds file.
        If group is specified, returns only that group as a dict.
        If no group is specified, returns all groups as a dict of dicts.

        Parameters:
            group (str, optional) : The group name to read. Default is None (read all).

        Example:
            data = eds.ReadData()
            product = eds.ReadData("Product")
            print(product["finalPrice"])  # 2950.0
        '''
        with open(self.Path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        allGroups = {}
        currentGroup = None
        currentFields = {}

        for line in lines:
            stripped = line.strip()

            if not stripped or stripped.startswith("--"):
                continue

            if not line.startswith("    ") and stripped.endswith(":"):
                if currentGroup:
                    allGroups[currentGroup] = self._evaluateGroup(currentFields)
                groupName = stripped[:-1].strip()
                if "{" in groupName:
                    groupName = groupName[:groupName.index("{")].strip()
                currentGroup = groupName
                currentFields = {}

            elif line.startswith("    ") and "=" in stripped:
                if "--" in stripped:
                    stripped = stripped[:stripped.index("--")].strip()
                key, _, rawValue = stripped.partition("=")
                key = key.strip()
                rawValue = rawValue.strip()
                currentFields[key] = rawValue

        if currentGroup:
            allGroups[currentGroup] = self._evaluateGroup(currentFields)

        if group:
            if group in allGroups:
                return allGroups[group]
            else:
                print(f"eds.GroupNotFoundError: Group '{group}' not found in file.")
                exit(1)

        return allGroups

    def _parseValue(self, raw):
        '''Parses a raw string value into the correct Python type.'''
        if raw.lower() == "true":
            return True
        if raw.lower() == "false":
            return False
        if raw.lower() == "null":
            return None
        if (raw.startswith('"') and raw.endswith('"')) or \
           (raw.startswith("'") and raw.endswith("'")):
            return raw[1:-1]
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            if not inner:
                return []
            items = [self._parseValue(item.strip()) for item in inner.split(",")]
            return items
        try:
            return int(raw)
        except ValueError:
            pass
        try:
            return float(raw)
        except ValueError:
            pass
        return raw

    def _evaluateGroup(self, fields):
        '''
        Evaluates all fields in a group.
        Only evaluates fields explicitly wrapped in arth().
        Everything else is parsed as-is.
        '''
        parsed = {}
        expressions = {}

        for key, raw in fields.items():
            if self._isExpression(raw):
                expressions[key] = raw[5:-1].strip()
            else:
                parsed[key] = self._parseValue(raw)

        for key, expr in expressions.items():
            try:
                result = eval(expr, {"__builtins__": {}}, parsed)
                if isinstance(result, float):
                    result = round(result, 2)
                parsed[key] = result
            except Exception:
                print(f"eds.ExpressionError: Could not evaluate arth({expr}) for key '{key}'.")
                exit(1)

        return parsed

    def _isExpression(self, raw):
        '''
        Checks if a value is an arth() expression.
        ONLY returns True if explicitly wrapped in arth().
        '''
        return raw.startswith("arth(") and raw.endswith(")")

    # ─────────────────────────────────────────────
    #  DELETE
    # ─────────────────────────────────────────────

    def DeleteData(self, group):
        '''
        Deletes an entire group and its fields from the .eds file.

        Parameters:
            group (str) : The group name to delete.

        Example:
            eds.DeleteData("Product")
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not self._groupExists(content, group):
            print(f"eds.GroupNotFoundError: Group '{group}' not found in file.")
            exit(1)

        lines = content.splitlines()
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith(group) and stripped.endswith(":"):
                i += 1
                while i < len(lines):
                    nextLine = lines[i]
                    if nextLine.startswith("    ") or nextLine.strip() == "":
                        i += 1
                    else:
                        break
            else:
                result.append(line)
                i += 1

        with open(self.Path, 'w', encoding='utf-8') as f:
            f.write("\n".join(result).strip() + "\n")

    # ─────────────────────────────────────────────
    #  UPDATE
    # ─────────────────────────────────────────────

    def UpdateData(self, group, key, value):
        '''
        Updates a single field inside a group.

        Parameters:
            group (str) : The group name.
            key   (str) : The field name to update.
            value       : The new value.

        Example:
            eds.UpdateData("Product", "basePrice", 3000)
            eds.UpdateData("Product", "finalPrice", "arth(basePrice * 1.18)")
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        if not isinstance(key, str):
            print("eds.KeyDataTypeError: Key name must be a string.")
            exit(1)

        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not self._groupExists(content, group):
            print(f"eds.GroupNotFoundError: Group '{group}' not found in file.")
            exit(1)

        lines = content.splitlines()
        result = []
        insideGroup = False
        keyFound = False
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if stripped.startswith(group) and stripped.endswith(":"):
                insideGroup = True
                result.append(line)

            elif insideGroup and not line.startswith("    ") and stripped != "":
                insideGroup = False
                result.append(line)

            elif insideGroup and line.startswith("    ") and "=" in stripped:
                lineKey = stripped.split("=")[0].strip()
                if lineKey == key:
                    keyFound = True
                    if isinstance(value, str):
                        if value.startswith("arth(") and value.endswith(")"):
                            result.append(f"    {key} = {value}")
                        else:
                            result.append(f'    {key} = "{value}"')
                    elif isinstance(value, list):
                        inner = ', '.join(
                            f"'{item}'" if isinstance(item, str) else str(item)
                            for item in value
                        )
                        result.append(f"    {key} = [{inner}]")
                    elif value is None:
                        result.append(f"    {key} = null")
                    elif isinstance(value, bool):
                        result.append(f"    {key} = {str(value).lower()}")
                    else:
                        result.append(f"    {key} = {value}")
                else:
                    result.append(line)
            else:
                result.append(line)

            i += 1

        if not keyFound:
            print(f"eds.KeyNotFoundError: Key '{key}' not found in group '{group}'.")
            exit(1)

        with open(self.Path, 'w', encoding='utf-8') as f:
            f.write("\n".join(result))

    # ─────────────────────────────────────────────
    #  GROUP EXISTS
    # ─────────────────────────────────────────────

    def GroupExists(self, group):
        '''
        Checks if a group exists in the .eds file.

        Parameters:
            group (str) : The group name to check.

        Returns:
            bool : True if group exists, False otherwise.

        Example:
            if eds.GroupExists("Product"):
                print("Found it!")
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        return self._groupExists(content, group)

    # ─────────────────────────────────────────────
    #  FILE INFO
    # ─────────────────────────────────────────────

    def SizeOfFile(self):
        '''
        Returns the size of the .eds file in bytes.

        Example:
            print(eds.SizeOfFile())  # 1024
        '''
        return Path(self.Path).stat().st_size

    def SizeOfGroup(self, group):
        '''
        Returns the size of a group block in bytes.

        Parameters:
            group (str) : The group name.

        Example:
            print(eds.SizeOfGroup("Product"))  # 512
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not self._groupExists(content, group):
            print(f"eds.GroupNotFoundError: Group '{group}' not found in file.")
            exit(1)

        lines = content.splitlines()
        block = []
        insideGroup = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(group) and stripped.endswith(":"):
                insideGroup = True
                block.append(line)
            elif insideGroup and line.startswith("    "):
                block.append(line)
            elif insideGroup:
                break
        return len("\n".join(block).encode("utf-8"))

    def GroupDatas(self, group):
        '''
        Returns the number of fields inside a group.

        Parameters:
            group (str) : The group name.

        Example:
            print(eds.GroupDatas("Product"))  # 5
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        data = self.ReadData(group)
        return len(data)

    def ListGroups(self):
        '''
        Returns a list of all group names in the .eds file.

        Example:
            print(eds.ListGroups())  # ['Product', 'Customer']
        '''
        with open(self.Path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        groups = []
        for line in lines:
            stripped = line.strip()
            if not line.startswith("    ") and stripped.endswith(":") and not stripped.startswith("--"):
                groupName = stripped[:-1].strip()
                if "{" in groupName:
                    groupName = groupName[:groupName.index("{")].strip()
                groups.append(groupName)
        return groups

    def CountGroups(self):
        '''
        Returns the total number of groups in the .eds file.

        Example:
            print(eds.CountGroups())  # 3
        '''
        return len(self.ListGroups())

    def RenameGroup(self, oldName, newName):
        '''
        Renames a group in the .eds file.

        Parameters:
            oldName (str) : The current group name.
            newName (str) : The new group name.

        Example:
            eds.RenameGroup("Product", "Item")
        '''
        if not isinstance(oldName, str) or not isinstance(newName, str):
            print("eds.GroupDataTypeError: Group names must be strings.")
            exit(1)

        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not self._groupExists(content, oldName):
            print(f"eds.GroupNotFoundError: Group '{oldName}' not found in file.")
            exit(1)

        if self._groupExists(content, newName):
            print(f"eds.GroupAlreadyExistsError: Group '{newName}' already exists in file.")
            exit(1)

        lines = content.splitlines()
        result = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(oldName) and stripped.endswith(":"):
                result.append(line.replace(oldName, newName, 1))
            else:
                result.append(line)

        with open(self.Path, 'w', encoding='utf-8') as f:
            f.write("\n".join(result))

    def ClearGroup(self, group):
        '''
        Removes all fields from a group but keeps the group header.

        Parameters:
            group (str) : The group name to clear.

        Example:
            eds.ClearGroup("Product")
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not self._groupExists(content, group):
            print(f"eds.GroupNotFoundError: Group '{group}' not found in file.")
            exit(1)

        lines = content.splitlines()
        result = []
        insideGroup = False
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith(group) and stripped.endswith(":"):
                insideGroup = True
                result.append(line)
            elif insideGroup and line.startswith("    "):
                pass
            else:
                insideGroup = False
                result.append(line)
            i += 1

        with open(self.Path, 'w', encoding='utf-8') as f:
            f.write("\n".join(result))

    # ─────────────────────────────────────────────
    #  FIELD-LEVEL OPERATIONS
    # ─────────────────────────────────────────────

    def AddField(self, group, key, value):
        '''
        Adds a single new field to an existing group without rewriting the whole group.

        Parameters:
            group (str) : The group name.
            key   (str) : The field name to add.
            value       : The value to set.

        Example:
            eds.AddField("Product", "brand", "Sony")
            eds.AddField("Product", "finalPrice", "arth(price * 1.18)")
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        if not isinstance(key, str):
            print("eds.KeyDataTypeError: Key name must be a string.")
            exit(1)

        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not self._groupExists(content, group):
            print(f"eds.GroupNotFoundError: Group '{group}' not found in file.")
            exit(1)

        existing = self.GroupToDict(group)
        if key in existing:
            print(f"eds.KeyAlreadyExistsError: Key '{key}' already exists in group '{group}'. Use UpdateData() instead.")
            exit(1)

        if isinstance(value, str):
            if value.startswith("arth(") and value.endswith(")"):
                newLine = f"    {key} = {value}"
            else:
                newLine = f'    {key} = "{value}"'
        elif isinstance(value, list):
            inner = ', '.join(f"'{i}'" if isinstance(i, str) else str(i) for i in value)
            newLine = f"    {key} = [{inner}]"
        elif value is None:
            newLine = f"    {key} = null"
        elif isinstance(value, bool):
            newLine = f"    {key} = {str(value).lower()}"
        else:
            newLine = f"    {key} = {value}"

        lines = content.splitlines()
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith(group) and stripped.endswith(":"):
                result.append(line)
                i += 1
                while i < len(lines) and (lines[i].startswith("    ") or lines[i].strip() == ""):
                    result.append(lines[i])
                    i += 1
                result.append(newLine)
            else:
                result.append(line)
                i += 1

        with open(self.Path, 'w', encoding='utf-8') as f:
            f.write("\n".join(result))

    def RemoveField(self, group, key):
        '''
        Removes a single field from a group.

        Parameters:
            group (str) : The group name.
            key   (str) : The field name to remove.

        Example:
            eds.RemoveField("Product", "discount")
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        if not isinstance(key, str):
            print("eds.KeyDataTypeError: Key name must be a string.")
            exit(1)

        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not self._groupExists(content, group):
            print(f"eds.GroupNotFoundError: Group '{group}' not found in file.")
            exit(1)

        lines   = content.splitlines()
        result  = []
        inside  = False
        keyFound = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(group) and stripped.endswith(":"):
                inside = True
                result.append(line)
            elif inside and line.startswith("    ") and "=" in stripped:
                lineKey = stripped.partition("=")[0].strip()
                if lineKey == key:
                    keyFound = True
                    pass  # skip = remove
                else:
                    result.append(line)
            else:
                if inside and not line.startswith("    "):
                    inside = False
                result.append(line)

        if not keyFound:
            print(f"eds.KeyNotFoundError: Key '{key}' not found in group '{group}'.")
            exit(1)

        with open(self.Path, 'w', encoding='utf-8') as f:
            f.write("\n".join(result))

    def GetField(self, group, key):
        '''
        Gets a single field value directly from a group.

        Parameters:
            group (str) : The group name.
            key   (str) : The field name to get.

        Returns:
            The value of the field (evaluated if arth()).

        Example:
            price = eds.GetField("Product", "finalPrice")
            print(price)  # 2950.0
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        if not isinstance(key, str):
            print("eds.KeyDataTypeError: Key name must be a string.")
            exit(1)

        data = self.ReadData(group)
        if key not in data:
            print(f"eds.KeyNotFoundError: Key '{key}' not found in group '{group}'.")
            exit(1)

        return data[key]

    def SortGroups(self):
        '''
        Sorts all groups alphabetically in the .eds file.

        Example:
            eds.SortGroups()
            # Before: ['Product', 'Zebra', 'Apple', 'Mango']
            # After:  ['Apple', 'Mango', 'Product', 'Zebra']
        '''
        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines        = content.splitlines()
        header       = []
        groups       = {}
        currentGroup = None
        inHeader     = True

        for line in lines:
            stripped = line.strip()
            if not line.startswith("    ") and stripped.endswith(":") and not stripped.startswith("--"):
                inHeader = False
                groupName = stripped[:-1].strip()
                if "{" in groupName:
                    groupName = groupName[:groupName.index("{")].strip()
                currentGroup = groupName
                groups[groupName] = [line]
            elif currentGroup and (line.startswith("    ") or stripped == ""):
                groups[currentGroup].append(line)
            elif inHeader:
                header.append(line)
            else:
                if currentGroup:
                    groups[currentGroup].append(line)

        result = header[:]
        for groupName in sorted(groups.keys()):
            block = groups[groupName]
            while block and block[-1].strip() == "":
                block.pop()
            result.extend(block)
            result.append("")

        with open(self.Path, 'w', encoding='utf-8') as f:
            f.write("\n".join(result))

    def SortFields(self, group):
        '''
        Sorts all fields inside a group alphabetically.

        Parameters:
            group (str) : The group name.

        Example:
            eds.SortFields("Product")
            # Before: ['name', 'price', 'inStock', 'discount']
            # After:  ['discount', 'inStock', 'name', 'price']
        '''
        if not isinstance(group, str):
            print("eds.GroupDataTypeError: Group name must be a string.")
            exit(1)

        with open(self.Path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not self._groupExists(content, group):
            print(f"eds.GroupNotFoundError: Group '{group}' not found in file.")
            exit(1)

        lines  = content.splitlines()
        result = []
        i = 0

        while i < len(lines):
            line     = lines[i]
            stripped = line.strip()
            if stripped.startswith(group) and stripped.endswith(":"):
                result.append(line)
                i += 1
                fieldLines = []
                while i < len(lines) and lines[i].startswith("    "):
                    fieldLines.append(lines[i])
                    i += 1
                fieldLines.sort(key=lambda l: l.strip().partition("=")[0].strip().lower())
                result.extend(fieldLines)
            else:
                result.append(line)
                i += 1

        with open(self.Path, 'w', encoding='utf-8') as f:
            f.write("\n".join(result))


# ─────────────────────────────────────────────
#  MODULE-LEVEL THREADING — BATCH OPERATIONS
# ─────────────────────────────────────────────

def BatchRead(filePaths, group=None):
    '''
    Reads multiple .eds files at once using threads — turbo fast!
    Returns a dict of { filePath: data }

    Parameters:
        filePaths (list)          : List of .eds file paths to read.
        group     (str, optional) : If specified, reads only that group from each file.

    Example:
        results = edsparse.BatchRead(['file1.eds', 'file2.eds'])
        print(results['file1.eds']['Product']['name'])

        # Read specific group from all files
        results = edsparse.BatchRead(['file1.eds', 'file2.eds'], group='Product')
        print(results['file1.eds']['name'])
    '''
    if not isinstance(filePaths, list):
        print("eds.BatchTypeError: filePaths must be a list of file path strings.")
        exit(1)

    results = {}
    errors  = {}
    lock    = threading.Lock()

    def _read(path):
        try:
            eds  = Open(path)
            data = eds.ReadData(group)
            with lock:
                results[path] = data
        except Exception as e:
            with lock:
                errors[path] = str(e)

    threads = [threading.Thread(target=_read, args=(p,)) for p in filePaths]
    for t in threads: t.start()
    for t in threads: t.join()

    if errors:
        for path, err in errors.items():
            print(f"eds.BatchReadError: Failed to read '{path}' — {err}")

    return results


def BatchWrite(writes):
    '''
    Writes data to multiple .eds files at once using threads — turbo fast!

    Parameters:
        writes (list) : List of dicts, each with keys:
                        - 'file'  (str)  : path to .eds file
                        - 'group' (str)  : group name to write
                        - 'data'  (dict) : fields to write

    Example:
        edsparse.BatchWrite([
            {'file': 'shop.eds',    'group': 'Product',  'data': {'name': 'Headphones', 'price': 2500}},
            {'file': 'users.eds',   'group': 'User1',    'data': {'name': 'Swastik',    'age': 10}},
            {'file': 'config.eds',  'group': 'AppConfig','data': {'debug': False,        'version': '1.0'}},
        ])
    '''
    if not isinstance(writes, list):
        print("eds.BatchTypeError: writes must be a list of dicts.")
        exit(1)

    errors = {}
    lock   = threading.Lock()

    def _write(entry):
        try:
            path  = entry.get('file')
            group = entry.get('group')
            data  = entry.get('data')
            if not path or not group or data is None:
                raise ValueError("Each entry must have 'file', 'group', and 'data' keys.")
            eds = Open(path)
            eds.WriteData(group, data)
        except Exception as e:
            with lock:
                errors[entry.get('file', '?')] = str(e)

    threads = [threading.Thread(target=_write, args=(entry,)) for entry in writes]
    for t in threads: t.start()
    for t in threads: t.join()

    if errors:
        for path, err in errors.items():
            print(f"eds.BatchWriteError: Failed to write '{path}' — {err}")


def BatchDelete(deletes):
    '''
    Deletes groups from multiple .eds files at once using threads.

    Parameters:
        deletes (list) : List of dicts with keys:
                         - 'file'  (str) : path to .eds file
                         - 'group' (str) : group name to delete

    Example:
        edsparse.BatchDelete([
            {'file': 'shop.eds',  'group': 'OldProduct'},
            {'file': 'users.eds', 'group': 'InactiveUser'},
        ])
    '''
    if not isinstance(deletes, list):
        print("eds.BatchTypeError: deletes must be a list of dicts.")
        exit(1)

    errors = {}
    lock   = threading.Lock()

    def _delete(entry):
        try:
            path  = entry.get('file')
            group = entry.get('group')
            if not path or not group:
                raise ValueError("Each entry must have 'file' and 'group' keys.")
            eds = Open(path)
            eds.DeleteData(group)
        except Exception as e:
            with lock:
                errors[entry.get('file', '?')] = str(e)

    threads = [threading.Thread(target=_delete, args=(entry,)) for entry in deletes]
    for t in threads: t.start()
    for t in threads: t.join()

    if errors:
        for path, err in errors.items():
            print(f"eds.BatchDeleteError: Failed to delete from '{path}' — {err}")


# ─────────────────────────────────────────────
#  MODULE-LEVEL UTILITY FUNCTIONS
# ─────────────────────────────────────────────

def CreateFile(path):
    '''
    Creates a brand new empty .eds file.

    Parameters:
        path (str) : Path where the new .eds file should be created.

    Example:
        edsparse.CreateFile("data/newfile.eds")
    '''
    if not isinstance(path, str):
        print("eds.FilePathDataTypeError: File path must be a string.")
        exit(1)

    if not path.lower().endswith(".eds"):
        print(f"eds.FileFormatError: File must have a .eds extension, got '{path}'.")
        exit(1)

    p = Path(path)
    if p.exists():
        print(f"eds.FileAlreadyExistsError: File '{path}' already exists.")
        exit(1)

    p.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write("# Created by EDSParse\n")

    return Open(path)


def MergeFiles(files, output):
    '''
    Merges multiple .eds files into one output file.
    If a group name exists in multiple files, the last one wins.

    Parameters:
        files  (list) : List of .eds file paths to merge.
        output (str)  : Path for the merged output .eds file.

    Example:
        edsparse.MergeFiles(['shop.eds', 'users.eds'], 'merged.eds')
    '''
    if not isinstance(files, list):
        print("eds.BatchTypeError: files must be a list.")
        exit(1)

    if not isinstance(output, str) or not output.lower().endswith(".eds"):
        print("eds.FileFormatError: output must be a .eds file path.")
        exit(1)

    merged = {}
    for path in files:
        eds = Open(path)
        data = eds.ReadData()
        merged.update(data)

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# Merged from: {', '.join(files)}\n"]
    for group, fields in merged.items():
        lines.append(f"{group}:")
        for key, value in fields.items():
            if isinstance(value, str):
                lines.append(f'    {key} = "{value}"')
            elif isinstance(value, list):
                inner = ', '.join(f"'{i}'" if isinstance(i, str) else str(i) for i in value)
                lines.append(f"    {key} = [{inner}]")
            elif value is None:
                lines.append(f"    {key} = null")
            elif isinstance(value, bool):
                lines.append(f"    {key} = {str(value).lower()}")
            else:
                lines.append(f"    {key} = {value}")
        lines.append("")

    with open(output, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    return Open(output)


def ExportToJSON(edsPath, jsonPath=None):
    '''
    Exports an .eds file to a JSON file.

    Parameters:
        edsPath  (str)           : Path to the .eds file.
        jsonPath (str, optional) : Path for the output JSON file.
                                   Defaults to same name as .eds file.

    Example:
        edsparse.ExportToJSON("shop.eds")            # creates shop.json
        edsparse.ExportToJSON("shop.eds", "out.json")
    '''
    if not jsonPath:
        jsonPath = edsPath.rsplit('.', 1)[0] + '.json'

    eds  = Open(edsPath)
    data = eds.ReadData()

    with open(jsonPath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

    print(f"eds.ExportToJSON: Exported '{edsPath}' → '{jsonPath}'")
    return jsonPath


def ImportFromJSON(jsonPath, edsPath=None):
    '''
    Imports a JSON file and converts it to an .eds file.
    Top-level keys become group names.

    Parameters:
        jsonPath (str)           : Path to the JSON file.
        edsPath  (str, optional) : Path for the output .eds file.
                                   Defaults to same name as JSON file.

    Example:
        edsparse.ImportFromJSON("shop.json")             # creates shop.eds
        edsparse.ImportFromJSON("shop.json", "data.eds")
    '''
    if not edsPath:
        edsPath = jsonPath.rsplit('.', 1)[0] + '.eds'

    with open(jsonPath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, dict):
        print("eds.ImportError: JSON root must be an object with group names as keys.")
        exit(1)

    lines = [f"# Imported from {jsonPath}\n"]
    for group, fields in data.items():
        if not isinstance(fields, dict):
            continue
        lines.append(f"{group}:")
        for key, value in fields.items():
            if isinstance(value, str):
                lines.append(f'    {key} = "{value}"')
            elif isinstance(value, list):
                inner = ', '.join(f"'{i}'" if isinstance(i, str) else str(i) for i in value)
                lines.append(f"    {key} = [{inner}]")
            elif value is None:
                lines.append(f"    {key} = null")
            elif isinstance(value, bool):
                lines.append(f"    {key} = {str(value).lower()}")
            else:
                lines.append(f"    {key} = {value}")
        lines.append("")

    with open(edsPath, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print(f"eds.ImportFromJSON: Imported '{jsonPath}' → '{edsPath}'")
    return Open(edsPath)


def CompareFiles(file1, file2):
    '''
    Compares two .eds files and returns a dict of differences.

    Parameters:
        file1 (str) : Path to the first .eds file.
        file2 (str) : Path to the second .eds file.

    Returns:
        dict with keys:
            - 'only_in_file1' : groups only in file1
            - 'only_in_file2' : groups only in file2
            - 'different'     : groups in both but with different field values
            - 'identical'     : groups that are exactly the same

    Example:
        diff = edsparse.CompareFiles("v1.eds", "v2.eds")
        print(diff['different'])
    '''
    eds1 = Open(file1)
    eds2 = Open(file2)
    data1 = eds1.ReadData()
    data2 = eds2.ReadData()
    keys1 = set(data1.keys())
    keys2 = set(data2.keys())

    result = {
        'only_in_file1' : list(keys1 - keys2),
        'only_in_file2' : list(keys2 - keys1),
        'different'     : [],
        'identical'     : [],
    }

    for group in keys1 & keys2:
        if data1[group] == data2[group]:
            result['identical'].append(group)
        else:
            diffs = {}
            all_keys = set(data1[group].keys()) | set(data2[group].keys())
            for key in all_keys:
                v1 = data1[group].get(key, '<<missing>>')
                v2 = data2[group].get(key, '<<missing>>')
                if v1 != v2:
                    diffs[key] = {'file1': v1, 'file2': v2}
            result['different'].append({group: diffs})

    return result


# ─────────────────────────────────────────────
#  INSTANCE-LEVEL NEW METHODS (added to Open)
# ─────────────────────────────────────────────

def _SearchValue(self, value):
    '''
    Searches all groups for a specific value.
    Returns a list of (group, key) tuples where the value was found.

    Parameters:
        value : The value to search for.

    Example:
        results = eds.SearchValue("Bengaluru")
        # [('Customer', 'city')]
    '''
    data    = self.ReadData()
    matches = []
    for group, fields in data.items():
        for key, val in fields.items():
            if val == value:
                matches.append((group, key))
    return matches


def _SearchGroup(self, query):
    '''
    Fuzzy searches group names — finds groups whose names contain the query.

    Parameters:
        query (str) : The search string (case-insensitive).

    Example:
        results = eds.SearchGroup("prod")
        # ['Product1', 'Product2']
    '''
    if not isinstance(query, str):
        print("eds.SearchTypeError: query must be a string.")
        exit(1)
    groups = self.ListGroups()
    return [g for g in groups if query.lower() in g.lower()]


def _DuplicateGroup(self, group, newName):
    '''
    Duplicates a group under a new name.

    Parameters:
        group   (str) : The group to duplicate.
        newName (str) : The name for the duplicated group.

    Example:
        eds.DuplicateGroup("Product1", "Product1_backup")
    '''
    if not isinstance(group, str) or not isinstance(newName, str):
        print("eds.GroupDataTypeError: Group names must be strings.")
        exit(1)

    with open(self.Path, 'r', encoding='utf-8') as f:
        content = f.read()

    if not self._groupExists(content, group):
        print(f"eds.GroupNotFoundError: Group '{group}' not found in file.")
        exit(1)

    if self._groupExists(content, newName):
        print(f"eds.GroupAlreadyExistsError: Group '{newName}' already exists.")
        exit(1)

    lines = content.splitlines()
    block = []
    insideGroup = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(group) and stripped.endswith(":"):
            insideGroup = True
            block.append(f"{newName}:")
        elif insideGroup and line.startswith("    "):
            block.append(line)
        elif insideGroup:
            break

    newBlock   = "\n".join(block)
    newContent = content.rstrip() + "\n\n" + newBlock + "\n"

    with open(self.Path, 'w', encoding='utf-8') as f:
        f.write(newContent)


def _GroupToDict(self, group):
    '''
    Returns the raw unevaluated fields of a group as a dict.
    arth() expressions returned as strings, not evaluated.

    Parameters:
        group (str) : The group name.

    Example:
        raw = eds.GroupToDict("Product")
        print(raw["finalPrice"])  # "arth(basePrice * (1 + taxRate))"
    '''
    if not isinstance(group, str):
        print("eds.GroupDataTypeError: Group name must be a string.")
        exit(1)

    with open(self.Path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    raw    = {}
    inside = False

    for line in lines:
        stripped = line.strip()
        if not line.startswith("    ") and stripped.endswith(":"):
            groupName = stripped[:-1].strip()
            if "{" in groupName:
                groupName = groupName[:groupName.index("{")].strip()
            if groupName == group:
                inside = True
            elif inside:
                break
        elif inside and line.startswith("    ") and "=" in stripped:
            if "--" in stripped:
                stripped = stripped[:stripped.index("--")].strip()
            key, _, val = stripped.partition("=")
            raw[key.strip()] = val.strip()

    if not raw and not inside:
        print(f"eds.GroupNotFoundError: Group '{group}' not found in file.")
        exit(1)

    return raw


def _FileStats(self):
    '''
    Returns a full summary of the .eds file.

    Example:
        stats = eds.FileStats()
        print(stats)
    '''
    data        = self.ReadData()
    totalFields = sum(len(fields) for fields in data.values())
    fileSize    = self.SizeOfFile()

    return {
        'file'         : self.Path,
        'size_bytes'   : fileSize,
        'size_kb'      : round(fileSize / 1024, 2),
        'total_groups' : len(data),
        'total_fields' : totalFields,
        'groups'       : {
            group: {
                'fields'     : len(fields),
                'size_bytes' : self.SizeOfGroup(group),
            }
            for group, fields in data.items()
        }
    }


# Bind new methods to Open class
Open.SearchValue    = _SearchValue
Open.SearchGroup    = _SearchGroup
Open.DuplicateGroup = _DuplicateGroup
Open.GroupToDict    = _GroupToDict
Open.FileStats      = _FileStats