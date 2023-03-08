from timeit import timeit

def format_name(name:str):
    """ Formate le nom d'un arrêt (eg. POISY_COLLÈGE -> Poisy collège)"""
    return name.replace("_", " ").capitalize()

class Horaire:
    """ Représente un horaire de bus """
    def __init__(self, hour:int=0, minute:int=0, day:int=0):
        self.day = day
        self.hour = hour
        self.minute = minute

    def duration(self, other):
        """Renvoie la durée entre deux horaires en minutes"""
        return (self.day - other.day) * 60 * 24 + (self.hour - other.hour) * 60 + self.minute - other.minute

    @staticmethod
    def from_scratch(text):
        """ Renvoie un objet horaire à partir d'un horaire de fichier txt (eg. 5:58 | 7:05 | - | 8:00)"""
        if text == "-": return None
        return Horaire(*map(int, text.split(":")))

    def __lt__(self, other):
        return self.hour < other.hour or self.minute < other.minute

    def __sub__(self, other):
        return Horaire(self.hour-other.hour, self.minute-other.minute)

    def __str__(self):
        return f"{self.hour:02d}:{self.minute:02d}"

    def __repr__(self):
        return self.__class__.__name__ + f' {self.hour}:{self.minute}'

class NoPathException(Exception):
    """ Exception lancée quand il n'existe aucun trajet entre deux arrets """
    pass

class Path:
    """ Représente un trajet direct ou indirect entre deux arrêts """
    def __init__(self, departure:Horaire, stops:list, arrival:Horaire):
        self.departure = departure
        self.stops = stops
        self.arrival = arrival

    def is_shorter(self, other):
        """ Compares number of stops """
        if len(self.stops) == len(other.stops):
            return self.is_foremost(other)
        return len(self.stops) < len(other.stops)

    def is_faster(self, other):
        """ Compares duration of stops """
        if self.duration() == other.duration():
            return self.is_foremost(other)
        return self.duration() < other.duration()

    def is_foremost(self, other):
        """ Compares time of arrivals of stops """
        return self.arrival < other.arrival

    def duration(self):
        return self.arrival.duration(self.departure)

    def __str__(self):
        return f"({self.departure}) {' -> '.join(stop.__str__() for stop in self.stops)} ({self.arrival})"

class Stop:
    """ Représente un arrêt de bus """
    cache:dict = dict()
    maxCache:int = 2048
    nbSkippedWithCache:int = 0
    def __init__(self, name:str, neighbors:list=None, neighborsWeekend:list=None):
        self.name = name
        # neighbors et neighborsWeekend sont des listes de tuples
        # - Horaire (l'horaire de départ)
        # - Horaire (l'horaire d'arrivée)
        # - Stop (l'arrêt d'arrivée)
        self.neighbors = [] if neighbors is None else neighbors
        self.neighborsWeekend = [] if neighborsWeekend is None else neighborsWeekend

    def paths(self, terminus:str, depart:Horaire, weekend:bool=False, _explored:set=None):
        """ Méthode principale, renvoie l'ensemble des chemins possibles entre deux arrêts"""
        explored = set()
        explored.add(self.name)
        if _explored is not None: explored.update(_explored)

        paths = []
        if self.name == terminus: return [Path(depart, [self], depart)]

        cacheTuple = (self.name, terminus, depart)
        # On utilise le cache
        if cacheTuple in Stop.cache:
            Stop.nbSkippedWithCache += 1
            return Stop.cache[cacheTuple]

        # On choisit des voisins à parcourir en fonction du jour
        neighborsToSearch = self.neighborsWeekend if weekend else self.neighbors
        for neighborDeparture, neighborArrival, neighbor in neighborsToSearch:
            # On skip le chemin si l'horaire est dépassé
            if neighborDeparture < depart: continue
            # On le skip s'il a déjà été traversé
            if neighbor.name in explored: continue

            for path in neighbor.paths(terminus, neighborArrival, weekend, explored):
                newPath = Path(neighborDeparture, self + path, path.arrival)
                paths.append(newPath)

        if len(Stop.cache) < Stop.maxCache: Stop.cache[cacheTuple] = paths

        return paths

    def best_paths(self, terminus:str, departure:Horaire, weekend:bool=False):
        """ Calcule les meilleurs chemins renvoyés par la méthode paths """
        paths:list[Path] = self.paths(terminus, departure, weekend)
        if not paths: raise NoPathException(f"Il n'existe pas de chemin entre \"{self.name}\" et \"{terminus}\" après {departure}")
        foremost, shortest, fastest = paths[0], paths[0], paths[0]
        for path in paths[1:]:
            if path.is_shorter(shortest): shortest = path
            if path.is_faster(fastest): fastest = path
            if path.is_foremost(foremost): foremost = path
        return len(paths), foremost, shortest, fastest

    def display_best_paths(self, terminus:str, departure:Horaire=Horaire(), weekend:bool=False):
        """ Affiche les chemins renvoyés par la méthode best_paths """
        try:
            bestPaths = self.best_paths(terminus, departure, weekend)
            print(f"Voici les meilleurs trajets pour aller de \"{self.name}\" à \"{terminus}\" parmi {bestPaths[0]:_} trajets:")
            print(f"Foremost: {bestPaths[1]}, durée: {bestPaths[1].duration()}m")
            print(f"Shortest: {bestPaths[2]}, durée: {bestPaths[2].duration()}m")
            print(f"Fastest: {bestPaths[3]}, durée: {bestPaths[3].duration()}m")
        except NoPathException as ex:
            print(ex)

    def filter(self, horaire: Horaire):
        """ Retourne l'arrêt avec tous les voisins accessibles à l'horaire donnée """
        return Stop(self.name, [
            neighbor
            for neighbor in self.neighbors
            if not(neighbor[0] < horaire)
        ])

    @staticmethod
    def reset_cache():
        Stop.cache = dict()
        Stop.nbSkippedWithCache = 0

    @staticmethod
    def display_cache():
        """ Affiche le contenu du cache formatée """
        for cache, paths in Stop.cache.items():
            res = f"{cache[0]} -> {cache[1]} ({cache[2]}):\n\t"
            res += '\n\t'.join(path.__str__() for path in paths) if paths else "Pas de chemin"
            print(res)

    @staticmethod
    def filterByHoraire(stops:dict, horaire:Horaire)->dict:
        """ Retourne un dictionnaire {nomArret: Arret} de tout les arrets filtrer par horaire """
        return {name: stop.filter(horaire) for name, stop in stops.copy().items()}

    def __add__(self, other):
        if isinstance(other, Stop): return [self, other]
        if isinstance(other, Path): return  [self] + other.stops

    def __str__(self):
        return self.name
        # neighborsCount = dict()
        # for neighbor in self.neighbors:
        #     if neighbor[2].name in neighborsCount: neighborsCount[neighbor[2].name] += 1
        #     else: neighborsCount[neighbor[2].name] = 1
        # return f"{self.name}, voisins: {' '.join(f'{name}(x {count})' for name, count in neighborsCount.items())}"

    def __repr__(self):
        return self.__class__.__name__ + f" {self.name}"

class Network:
    """ Représente un réseau de bus """
    def __init__(self, stops:list[Stop]=None):
        self.stops = stops if stops else []

    def __contains__(self, name)->bool:
        if not isinstance(name, str): raise AttributeError
        for stop in self.stops:
            if stop.name == name: return True
        return False

    def __getitem__(self, key)->Stop:
        if isinstance(key, str):
            for stop in self.stops:
                if stop.name == key: return stop
            raise KeyError(f"L'arrêt \"{key}\" n'existe pas")
        if isinstance(key, int):
            return self.stops[key]
        raise KeyError(f"{key.__class__.__name__} n'est pas une clé valide")

    def __add__(self, other):
        if not isinstance(other, Network): raise AttributeError(f"{other.__class__.__name__} n'est pas un Network")
        for stopToMerge in other.stops:
            try:
                stop = self[stopToMerge.name]
                stop.neighbors += stopToMerge.neighbors
                stop.neighborsWeekend += stopToMerge.neighborsWeekend
            except KeyError:
                self.stops.append(stopToMerge)
        return self


    @staticmethod
    def parseFiles(filesPath:list[str]):
        """ Transforme plusieurs fichiers d'horaires en un réseau """
        network = Network()
        for filePath in filesPath:
            network += Network.parseFile(filePath)
        return network

    @staticmethod
    def parseFile(filePath:str):
        """ Transforme un fichier d'horaires en un réseau """
        with open(filePath, "r", encoding="utf8") as file:
            paragraphs = file.read().split("\n\n")

        # Initialisation des arrets
        network = Network([
            Stop(format_name(stop))
            for stop in paragraphs[0].split(" N ")
        ])
        paragraphs = paragraphs[1], paragraphs[2], paragraphs[4], paragraphs[5]

        # TODO : prendre en compte les horaires weekend
        # Ajout des liens entre arrêts pour chaque paragraphe
        for i, paragraph in enumerate(paragraphs):
            horaires = [
                [
                    Horaire.from_scratch(horaire)
                    for horaire in ligne.split(" ")[1:]
                ]
                for ligne in paragraph.split("\n")
            ]

            # On transpose la "matrice" des horaires pour obtenir les colonnes
            horaireColumns = list(zip(*horaires))

            # Gestion différente selon chaque paragraphe
            if i == 0:
                network.addHoraires(horaireColumns, reverse=False, weekend=False)
            if i == 1:
                network.addHoraires(horaireColumns, reverse=True, weekend=False)
            if i == 2:
                network.addHoraires(horaireColumns, reverse=False, weekend=True)
            if i == 3:
                network.addHoraires(horaireColumns, reverse=True, weekend=True)
        return network

    def addHoraires(self, horaires: list[tuple], reverse:bool=False, weekend:bool = False):
        """ Ajoute des voisins aux différents arrêts (c'est un brainfuck, soyez prévenus) """
        for fuseau in horaires:
            oldArret, newArret, oldHoraire = None, None, None
            for iArret, horaire in enumerate(fuseau):
                # Cas de l'horaire vide "-"
                if horaire is None: continue
                newArret = self[-iArret if reverse else iArret]
                if oldArret is not None:
                    if weekend:
                        oldArret.neighborsWeekend.append((oldHoraire, horaire, newArret))
                    else:
                        oldArret.neighbors.append((oldHoraire, horaire, newArret))
                oldArret, oldHoraire = self[-iArret if reverse else iArret], horaire

    def __str__(self):
        return " | ".join(stop.name for stop in self.stops)


def displayBestPaths(departure:Stop, arrivals:dict, horaires:list[Horaire], weekend:bool=False):
    """ Affiche les meilleurs chemins d'un arret à tout les autres, pour différentes horaires """
    for horaire in horaires:
        print("-----",horaire,"-----")
        stopsFiltered = Stop.filterByHoraire(arrivals, horaire)
        for arrival in stopsFiltered.values():
            try:
                departure.display_best_paths(arrival.name, horaire, weekend)
            except NoPathException as ex: print(ex)
            finally:
                print("Cache hits:", Stop.nbSkippedWithCache)
                print()
        Stop.reset_cache()

def displayStats(departure:Stop, arrivals:dict, horaires:list[Horaire]):
    """ Affiche les statistiques (durée, nombre de chemins, cache hits) lors du calcul de trajet d'un arret à tout les autres, pour différentes horaires """
    for horaire in horaires:
        print("-----",horaire,"-----")
        stopsDicoFiltered = Stop.filterByHoraire(arrivals, horaire)
        for arrival in stopsDicoFiltered.values():
            try:
                timeTaken = timeit(lambda: departure.best_paths(arrival.name, horaire), number=1)
                print(f"✔️Chemins entre \"{departure.name}\" et \"{arrival.name}\"")
                print(f"Durée execution: {timeTaken:.2f}")
            except NoPathException:
                print(f"❌   Pas de chemin entre \"{departure.name}\" et \"{arrival.name}\"")
        Stop.reset_cache()

if __name__ == "__main__":
    files = [
        "data/test_enonce.txt",
        "data/test.txt",
        "data/1_Poisy-ParcDesGlaisins.txt",
        "data/2_Piscine-Patinoire_Campus.txt"
    ]

    # network = Network.parseFiles(files)
    network = Network.parseFile(files[1])

    print("Réseau importé: ", network, "\n")
    departure = network["Arret1"]

    # defaultHoraires = [Horaire(14, 30), Horaire(8, 30), Horaire(6, 30)]
    # displayBestPaths(departure, stopsDict, [Horaire(6)], weekend=False)
    # displayStats(departure, stopsDico, defaultHoraires)

    departure.display_best_paths("Arret5")
