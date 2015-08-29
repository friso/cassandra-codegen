# cassandra-codegen
Trivial utility to generate Cassandra DDL (CQL) and Java8 immutable POJOs from a YAML file describing the database schema.

## Installation

```sh
pip install -U git+https://github.com/friso/cassandra-codegen.git
```
## Example

### Table and type specification
```yaml
---
options:
  package: com.example.dto
  keyspace: example

types:
  nested_type:
    foo: varchar
    other_field: int
    complex_field:
      type: map
      keys: int
      values: varchar
  user_type:
    bar: int
    nested: nested_type

tables:
  my_table:
    fields:
      pk_string: varchar
      pk_long: bigint
      rim: timeuuid
      ram: timestamp
      float_list:
        type: list
        entries: float
    partition_key:
      - pk_string
      - pk_long
    clustering:
      rim: desc
      ram: asc
    options:
      comment: This text will be outdated soon.
      compaction:
        class: SizeTieredCompactionStrategy
        min_threshold: 6
```

### Generated CQL
```cql
USE example;

CREATE TYPE nested_type (
  foo varchar,
  other_field int,
  complex_field map<int,varchar>
);

CREATE TYPE user_type (
  bar int,
  nested frozen<nested_type>
);


CREATE TABLE my_table (
  pk_string varchar,
  pk_long bigint,
  rim timeuuid,
  ram timestamp,
  float_list list<float>,
  PRIMARY KEY ((pk_string, pk_long), rim, ram)
) WITH
  CLUSTERING ORDER BY (rim DESC, ram ASC) AND
  comment = 'This text will be outdated soon.' AND
  compaction = { 'class': 'SizeTieredCompactionStrategy', 'min_threshold': 6 };
```

### Generated Java

`NestedType.java`:
```java
package com.example.dto;

import com.datastax.driver.core.KeyspaceMetadata;
import com.datastax.driver.core.UDTValue;

@SuppressWarnings("all")
public final class NestedType {
    public final String foo;
    public final int otherField;
    public final java.util.Map<Integer,String> complexField;
    
    public NestedType(
            final String foo,
            final int otherField,
            final java.util.Map<Integer,String> complexField) {
        this.foo = foo;
        this.otherField = otherField;
        this.complexField = complexField;
    }

    public NestedType(final com.datastax.driver.core.UDTValue value) {
        this.foo = value.getString("foo");
        this.otherField = value.getInt("other_field");
        this.complexField = value.getMap("complex_field", Integer.class, String.class);
    }

    public UDTValue toUDTValue(final KeyspaceMetadata meta) {
        final UDTValue value = meta.getUserType("nested_type").newValue();
        value.setString("foo", foo);
        value.setInt("other_field", otherField);
        value.setMap("complex_field", complexField);
        return value;
    }
}
```

`UserType.java`:
```java
package com.example.dto;

import com.datastax.driver.core.KeyspaceMetadata;
import com.datastax.driver.core.UDTValue;

@SuppressWarnings("all")
public final class UserType {
    public final int bar;
    public final NestedType nested;
    
    public UserType(
            final int bar,
            final NestedType nested) {
        this.bar = bar;
        this.nested = nested;
    }

    public UserType(final com.datastax.driver.core.UDTValue value) {
        this.bar = value.getInt("bar");
        this.nested = new NestedType(value.getUDTValue("nested"));
    }

    public UDTValue toUDTValue(final KeyspaceMetadata meta) {
        final UDTValue value = meta.getUserType("user_type").newValue();
        value.setInt("bar", bar);
        value.setUDTValue("nested", nested.toUDTValue(meta));
        return value;
    }
}
```

`MyTable.java`:
```java
package com.example.dto;

import static com.datastax.driver.core.querybuilder.QueryBuilder.*;

import java.util.stream.StreamSupport;

import com.datastax.driver.core.KeyspaceMetadata;
import com.datastax.driver.core.ResultSet;
import com.datastax.driver.core.Row;
import com.datastax.driver.core.Session;
import com.datastax.driver.core.Statement;
import com.datastax.driver.core.querybuilder.QueryBuilder;
import com.datastax.driver.core.querybuilder.Select;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableList.Builder;

@SuppressWarnings("all")
public final class MyTable {
    public final String pkString;
    public final long pkLong;
    public final java.util.UUID rim;
    public final java.time.Instant ram;
    public final java.util.List<Float> floatList;
    
    public static final MyTableFields fields = new MyTableFields();
    public static final String table = "my_table";
    public static final String keyspace = "example";

    public static class MyTableFields {
        private MyTableFields() {}
        public final String pkString = "pk_string";
        public final String pkLong = "pk_long";
        public final String rim = "rim";
        public final String ram = "ram";
        public final String floatList = "float_list";
    }

    public MyTable(
            final String pkString,
            final long pkLong,
            final java.util.UUID rim,
            final java.time.Instant ram,
            final java.util.List<Float> floatList) {
        this.pkString = pkString;
        this.pkLong = pkLong;
        this.rim = rim;
        this.ram = ram;
        this.floatList = floatList;
    }
    
    public static java.util.List<MyTable> all(final ResultSet result) {
        Builder<MyTable> builder = ImmutableList.builder();
        StreamSupport
            .stream(result.spliterator(), false)
            .map(MyTable::fromRow)
            .forEach(builder::add);
        return builder.build();
    }

    public static MyTable one(final ResultSet rs) {
        return fromRow(rs.one());
    }

    private static MyTable fromRow(final Row row) {
        return new MyTable(
        row.getString("pk_string"),
        row.getLong("pk_long"),
        row.getUUID("rim"),
        row.getDate("ram").toInstant(),
        row.getList("float_list", Float.class));
    }

    public static Select select(final Session session) {
        return QueryBuilder
          .select()
          .all()
          .from(keyspace, table);
    }

    public Statement insert(final Session session) {
        final KeyspaceMetadata meta = session.getCluster().getMetadata().getKeyspace("example");
        return QueryBuilder
                .insertInto(keyspace, table)
                .value("pk_string", pkString)
                .value("pk_long", pkLong)
                .value("rim", rim)
                .value("ram", new java.util.Date(ram.toEpochMilli()))
                .value("float_list", floatList);
    }

    public Statement update(final Session session) {
        final KeyspaceMetadata meta = session.getCluster().getMetadata().getKeyspace("example");
        return QueryBuilder
                .update(keyspace, table)
                .with(set("float_list", floatList))
                .where(eq("pk_string", pkString))
                .and(eq("pk_long", pkLong))
                .and(eq("rim", rim))
                .and(eq("ram", new java.util.Date(ram.toEpochMilli())));
    }

    public Statement delete(final Session session) {
        final KeyspaceMetadata meta = session.getCluster().getMetadata().getKeyspace("example");
        return QueryBuilder
                .delete()
                .from(keyspace, table)
                .where(eq("pk_string", pkString))
                .and(eq("pk_long", pkLong))
                .and(eq("rim", rim))
                .and(eq("ram", new java.util.Date(ram.toEpochMilli())));
    }
}
```

## Usage
The main command is `ccgen`. The tool allows to specify where to create the CQL DDL script and the base directory for the Java sources. Subdirectories for packages will be created if they do not exist.

The script takes a YAML file that describes the Cassandra user defined types and tables to create. See the next section for syntax.

```sh
$ ccgen -h
usage: ccgen [-h] [--java JAVA_OUTPUT_DIR] [--cql CQL_FILE]
             YAML_FILES [YAML_FILES ...]

Generate CQL DDL and Java POJOs from YAML descriptions of Cassandra tables.

positional arguments:
  YAML_FILES            YAML files with table descriptions to parse. Multiple
                        files may be specified.

optional arguments:
  -h, --help            show this help message and exit
  --java JAVA_OUTPUT_DIR, -j JAVA_OUTPUT_DIR
                        Output directory for the generated Java source files.
                        Directories for packages will be created underneath if
                        they do not exist.
  --cql CQL_FILE, -c CQL_FILE
                        File name for the generated CQL file. Fully qualified
                        directory and filename (e.g. src/generated/cql/create-
                        tables.cql)
```

## Caveats
- `timestamp` fields will be `java.time.Instant`, not `java.util.Date`.
- Cassandra `tuple` type is not supported.
- Generated source code is compatible with Java >= 8.
