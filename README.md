# Bibliotheek Midden-Brabant open data dashboard
Deze repository is gemaakt in samenwerking met Bibliotheek Midden-Brabant en Tau Omega. Het doel is om zo makkelijk 
mogelijk open data van de omgeving Tilburg te visualiseren. Daardoor kan programmering gemaakt worden over onderwerpen 
die te maken hebben met de Sustainable Development Goals. 

## Installatie
Om het dashboard te installeren moet je de repository _clonen/downloaden_ en een python environment maken waar alle 
software geïnstalleerd kan worden. Het wordt aangeraden om de software te installeren via ```conda```. Deze kan hier 
gedownload worden: [https://www.anaconda.com/products/individual](https://www.anaconda.com/products/individual).

Wanneer Anaconda is gedownload kan je met de volgende code een environment maken (zorg dat je in de repository map zit):
```conda env create -f bmb_env.yml```. Er is ook een ```requirements.txt``` toegevoegd zodat er ook op andere manieren 
packages geïnstalleerd kunnen worden.

Als alles correct is geïnstalleerd, dan kan het dashboard opgestard worden met: ```python core/index.py```. Dan kan je 
via de localhost server naar het dashboard gaan (dit zal lijken op: ```http://127.0.0.1:8050```).

## Het dashboard
Het dashboard is gemaakt met Plotly Dash en deze draait op Flask. In de map ```core``` staat alle code van het dashboard
en deze is onderverdeeld in drie mappen: ```apps```, ```assets``` en ```datasets```. De python files in ```core``` zelf 
zijn losse functies of om het dashboard op te starten. In de map ```apps``` staan de verschillende pagina's. In 
```assets``` staan bestanden die worden gebruikt voor de style van het dashboard (css bestanden en lettertypes). In 
```datasets``` worden data bestanden gezet (shape-files en coordinaten van de ringbaan). Daarnaast staan er ook een paar
voorbeeld datasets in.