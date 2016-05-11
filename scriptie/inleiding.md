# Inleiding

Dit document is geschreven als begeleiding bij de opgeleverde *Misofome*
web applicatie. Het beschrijft het afstudeerproces wat heeft geleid
tot het eindproduct. De applicatie is ontwikkeld ter ondersteuning
van de behandeling van misofonie aan de afdeling angststoornissen van
het Academisch Medisch Centrum te Amsterdam. Gebruikers kunnen in de
applicatie een crowd sourced verzameling van oefeningen raadplegen.

Het de applicatie is opgebouwd uit drie componenten, een database,
een server applicatie (API) en een frontend (in de browser). Deze
componenten staan los van elkaar maar communiceren om het geheel te
maken. Het is mogelijk om de componenten uit te wisselen voor andere
implementaties. Meer hierover in het hoofdstuk over architectuur.

```
+-------------+       +-------------+        +-------------+
|             |       |             |        |             |
|             |       |             |        |             |
|             +------->             +-------->             |
|  Database   |       |   Web API   |        | Smartphone  |
|             |       |             |        |             |
|             <-------+             <--------+             |
|             |       |             |        |             |
+-------------+       +-------------+        +-------------+
```

De directe opdrachtgever en contact persoon was Pieter Ooms. Hij was
tevens één van de belangrijkste bronnen van informatie over het
domein. Fons van Kesteren was de afstudeerbegeleider en had meer inzicht
in het technische aspect van het project.

<!-- TODO voeg link toe -->
Het eindproduct is [hier](link.to.app) te vinden. Het is ontwikkeld voor
de telefoon maar is ook bereikbaar in de normale browser.
