## 1. Retrieving and Filtering Data (READ)

**Basic Patterns**

* `MATCH (n:Label)` → Find all nodes with label.
* `MATCH (n:Person {name:'John'})` → Node with property filter.
* `MATCH (a:Actor)-[:ACTED_IN]->(m:Movie)` → Relationship match.

**Filtering**

* `WHERE n.year > 2000` → Apply conditions.
* `RETURN n.name, m.title` → Select fields to output.

**Ordering, Limiting**

* `ORDER BY n.name DESC`
* `LIMIT 10`
* `SKIP 10 LIMIT 10`

---

## 2. Creating and Updating Data (WRITE)

**Create**

* `CREATE (n:Label {prop:'value'})`
* `CREATE (p:Person)-[:WORKS_AT]->(c:Company)`

**Update**

* `SET n.age = 30`
* `SET n += {props}` → multiple props at once.
* `REMOVE n.age`, `REMOVE n:Label`

**Delete**

* `DELETE n`
* `DETACH DELETE n` → delete node and relationships.

---

## 3. Schema and Utilities

**MERGE**

* `MERGE (p:Person {name:'Jane'})` → find or create.

**Procedures (`CALL …`)**

* `CALL db.schema.visualization()` → visualize schema.
* `CALL db.labels()` → list all labels.
* `CALL db.relationshipTypes()` → list relationship types.
* `CALL db.propertyKeys()` → list all property keys.
* `CALL db.schema.nodeTypeProperties()` - list all property types for nodes in the graph.
* `CALL db.schema.relTypeProperties()` - list all property types for relationships in the graph.

**Indexes & Constraints**

* `CREATE INDEX FOR (n:Label) ON (n.prop)`
* `CREATE CONSTRAINT FOR (n:Label) REQUIRE n.prop IS UNIQUE`
* `SHOW CONSTRAINTS`

---

## 4. Aggregation & Functions

* `COUNT(n)` → count results.
* `COLLECT(n)` → gather into a list.
* `AVG(n.age)`, `MIN(n.age)`, `MAX(n.age)`
* `SIZE(n.listProp)` → list size.

---

## 5. Advanced Patterns

* **Optional matches**:
  `OPTIONAL MATCH (n)-[:FRIEND]->(m)` → returns null if no match.
* **Path queries**:
  `MATCH p=(a)-[*1..3]->(b) RETURN p` → variable-length paths.
* **Unwind lists**:
  `UNWIND [1,2,3] AS x RETURN x`



EXPLAIN, PROFILE, 
ENDS/STARTS WITH
CONTAINS
toLower
collect
[]
count, count *