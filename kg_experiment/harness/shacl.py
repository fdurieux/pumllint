"""D4: an RDF projection of the graph, validated with pyshacl.

The projection is Python-side (rdflib) from Cypher reads; n10s is not
executed. Two shapes graphs: the main one mirrors R-STRUCT and R-REQ;
the second has a single sh:Info-severity shape that every assertion
violates, to show at execution that sh:conforms is false on
information-level results alone (SHACL §2.1.4, §3.6.1.1).
"""

from __future__ import annotations

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, URIRef

KG = Namespace("urn:kg:")
SH = Namespace("http://www.w3.org/ns/shacl#")

SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix kg: <urn:kg:> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

kg:SourcedAssertionShape a sh:NodeShape ;
    sh:targetClass kg:SourcedAssertion ;
    sh:property [ sh:path kg:supportedBy ; sh:minCount 1 ;
                  sh:message "an extracted or authored assertion needs a supporting fragment" ] ;
    sh:property [ sh:path kg:status ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:string ] .

kg:InferredAssertionShape a sh:NodeShape ;
    sh:targetClass kg:InferredAssertion ;
    sh:property [ sh:path kg:candidateFor ; sh:minCount 1 ;
                  sh:message "an inferred assertion must be linked to the gap it proposes to fill" ] .

kg:RequirementShape a sh:NodeShape ;
    sh:targetClass kg:Requirement ;
    sh:property [ sh:path kg:verifiedBy ; sh:minCount 1 ; sh:severity sh:Warning ;
                  sh:message "a requirement needs a verifying scenario" ] .

kg:FragmentShape a sh:NodeShape ;
    sh:targetClass kg:Fragment ;
    sh:property [ sh:path kg:ofVersion ; sh:minCount 1 ; sh:maxCount 1 ] .
"""

INFO_SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix kg: <urn:kg:> .

kg:CommentShape a sh:NodeShape ;
    sh:targetClass kg:SourcedAssertion ;
    sh:property [ sh:path kg:reviewerComment ; sh:minCount 1 ; sh:severity sh:Info ;
                  sh:message "no reviewer comment recorded (informational)" ] .
"""


def project(s) -> Graph:
    g = Graph()
    g.bind("kg", KG)
    for r in s.run("MATCH (x:Assertion) RETURN x.id AS id, x.basis AS basis, x.status AS status"):
        n = URIRef(KG[r["id"].replace("|", "_").replace(" ", "_")])
        cls = KG.InferredAssertion if r["basis"] in ("inferred", "assumed", "hypothesised") else KG.SourcedAssertion
        g.add((n, RDF.type, cls))
        g.add((n, KG.status, Literal(r["status"])))
    for r in s.run("MATCH (x:Assertion)-[:SUPPORTED_BY]->(f:Fragment) RETURN x.id AS x, f.id AS f"):
        g.add((URIRef(KG[r["x"].replace("|", "_").replace(" ", "_")]), KG.supportedBy, URIRef(KG[r["f"].replace(" ", "_")])))
    for r in s.run("MATCH (x:Assertion)-[:CANDIDATE_FOR]->(g:Gap) RETURN x.id AS x, g.id AS g"):
        g.add((URIRef(KG[r["x"].replace("|", "_").replace(" ", "_")]), KG.candidateFor, URIRef(KG[r["g"]])))
    for r in s.run("MATCH (f:Fragment) OPTIONAL MATCH (v:Version)-[:HAS_FRAGMENT]->(f) RETURN f.id AS f, v.id AS v"):
        fn = URIRef(KG[r["f"].replace(" ", "_")])
        g.add((fn, RDF.type, KG.Fragment))
        if r["v"]:
            g.add((fn, KG.ofVersion, URIRef(KG[r["v"].replace(" ", "_")])))
    for r in s.run("MATCH (e:Entity {kind:'requirement'}) OPTIONAL MATCH (x:Assertion {predicate:'verified_by'})-[:ABOUT]->(e) RETURN e.id AS e, collect(x.value) AS by"):
        en = URIRef(KG[r["e"]])
        g.add((en, RDF.type, KG.Requirement))
        for b in r["by"]:
            g.add((en, KG.verifiedBy, URIRef(KG[b])))
    return g


def run(s) -> dict:
    data = project(s)
    out = {"triples": len(data)}
    for name, shapes in (("main", SHAPES), ("info_only", INFO_SHAPES)):
        sg = Graph().parse(data=shapes, format="turtle")
        conforms, results_graph, text = validate(data, shacl_graph=sg, inference="none", abort_on_first=False)
        n = len(list(results_graph.subjects(RDF.type, SH.ValidationResult)))
        sev = {}
        for res in results_graph.subjects(RDF.type, SH.ValidationResult):
            sv = results_graph.value(res, SH.resultSeverity)
            sev[str(sv).split("#")[-1]] = sev.get(str(sv).split("#")[-1], 0) + 1
        out[name] = {"conforms": bool(conforms), "results": n, "by_severity": sev,
                     "sample": text.splitlines()[:12]}
    return out
