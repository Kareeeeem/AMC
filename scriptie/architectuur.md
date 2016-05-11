# Architectuur

In dit hoofdstuk wordt de opbouw van het product beschreven. De gemaakte
keuzes hierin zijn voornamelijk geïnformeerd door de volgende eisen;

* *Seperation of concerns*: dit betekend heel simpel dat de
  verschillende componenten van een oplossing zich enkel bezig houden
  met hun eigen verantwoordelijkheden. Een component dat zich bezig houd
  met het opslaan en verwerken van scores hoeft bijvoorbeeld niet te
  weten hoe deze scores worden getoond aan de gebruiker.

* Overdraagbaarheid: het is de bedoeling dat andere studenten volgend
  jaar weer aan de slag gaan met het product wat is opgeleverd. Zij
  zullen de feedback van de patiënten en de resultaten van hun eigen
  tests gebruiken om verbeteringen aan te brengen. Om dit mogelijk te
  maken moet het duidelijk in elkaar zitten en de geschreven code
  geschreven zijn met leesbaarheid hoog in het vaandel.

* Flexibiliteit: het product is nog steeds in een experimentele fase.
  Het moet mogelijk zijn om terug te komen op gemaakte keuzes en deze te
  veranderen.

## Backend

De backend applicatie is geschreven in *Python*. Python is een
high-level programmeer taal met een hoge focus op leesbaarheid.
High-level refereert naar de vele abstracties die de taal biedt aan de
ontwikkelaar, deze hoeft geen rekening te houden met hoe de computer de
code zal uitvoeren. Veel Python code heeft meer weg van Engels dan wat
je zou voorstellen als instructie voor een computer. Het volgende
fragment is valide code voor bijvoorbeeld het managen van een
gastenlijst op een feestje.

```
guests = ['Kareem', 'Hajar', 'Daniyah', 'Stanger']

if 'Stranger' in list_of_guests:
    guests.remove('Stranger')
```

Dit is de alom bekende "Hello, World!" in python.

```
print("hello world")
```

Vergelijk dit met de "Hello, World!" applicatie in C.

```
#include <stdio.h>

int main() {
    printf("%s", "Hello, World!")
    return 0
}
```

Of in Java.

```
public class HelloWorld {

    public static void main(String[] args) {
        System.out.println("Hello, World");
    }
}
```

Er zijn natuurlijk ook nadelen aan zo'n expressieve taal als Python. Het
is bijvoorbeeld niet geschikt om extreem snelle software te ontwikkelen,
of software dat runt op hele kleine computers die in apparaten verwerkt
zijn. Echter dan hebben we het over software voor bijvoorbeeld medische
apparatuur, en niet een web applicatie zoals deze. Als voorbeelden van
Python in de "echte wereld" zijn er [reddit](www.reddit.com) en
[intragram](www.instragram.com), beide geschreven in Python.
