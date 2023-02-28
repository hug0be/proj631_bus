from timeit import timeit

def format_name(name:str):
    """ Formats the name of a stop (eg. POISY_COLLÈGE -> Poisy collège)"""
    return name.replace("_", " ").capitalize()

class Horaire:
    def __init__(self, hour:int, minute:int=0, day:int=0):
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

class NoPathException(Exception):
    """ Exception raised when no path exists between two stops """
    pass

class Path:
    """ Represents the path between two stops
    departure: time of departure
    stops: explored stops
    arrival: time of arrival"""
    def __init__(self, departure:Horaire, stops:list, arrival:Horaire):
        self.departure = departure
        self.arrival = arrival
        self.stops = stops

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
    cache:dict = dict()
    maxCache:int = 2048
    nbSkippedWithCache:int = 0
    def __init__(self, name:str, neighbors:list=None):
        self.name = name
        self.neighbors = [] if neighbors is None else neighbors
        # neighbors est une liste de tuples
        # - Horaire (l'horaire de départ)
        # - Horaire (l'horaire d'arrivée)
        # - Stop (l'arrêt d'arrivée)

    def paths(self, terminus:str, depart:Horaire, _explored:set=None):
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

        for neighborDeparture, neighborArrival, neighbor in self.neighbors:

            # On skip le chemin si l'horaire est dépassé
            if neighborDeparture < depart: continue
            # On le skip s'il a déjà été traversé
            if neighbor.name in explored: continue

            for path in neighbor.paths(terminus, neighborArrival, explored):
                newPath = Path(neighborDeparture, self + path, path.arrival)
                paths.append(newPath)

        if len(Stop.cache) < Stop.maxCache: Stop.cache[cacheTuple] = paths

        return paths

    def best_paths(self, terminus:str, departure:Horaire):
        paths:list[Path] = self.paths(terminus, departure)
        if not paths: raise NoPathException
        foremost, shortest, fastest = paths[0], paths[0], paths[0]
        for path in paths[1:]:
            if path.is_shorter(shortest): shortest = path
            if path.is_faster(fastest):
                fastest = path
            if path.is_foremost(foremost): foremost = path
        return len(paths), foremost, shortest, fastest

    def display_best_paths(self, terminus:str, departure:Horaire):
        bestPaths = self.best_paths(terminus, departure)
        print(f"Voici les meilleurs trajets pour allez de \"{self.name}\" à \"{terminus}\" parmi {bestPaths[0]:_} trajets:")
        print(f"Foremost: {bestPaths[1]}, durée: {bestPaths[1].duration()}m")
        print(f"Shortest: {bestPaths[2]}, durée: {bestPaths[2].duration()}m")
        print(f"Fastest: {bestPaths[3]}, durée: {bestPaths[3].duration()}m")

    def filter(self, horaire: Horaire):
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
        for cache, paths in Stop.cache.items():
            res = f"{cache[0]} -> {cache[1]} ({cache[2]}):\n\t"
            res += '\n\t'.join(path.__str__() for path in paths) if paths else "Pas de chemin"
            print(res)

    @staticmethod
    def add_horaires(horaires, arrets):
        for ligne in horaires:
            oldArret, newArret, oldHoraire = None, None, None
            for iArret, horaire in enumerate(ligne):
                if horaire is None: continue
                newArret = arrets[iArret]
                if oldArret is not None:
                    oldArret.neighbors.append((oldHoraire, horaire, newArret))
                oldArret, oldHoraire = arrets[iArret], horaire
        return arrets

    @staticmethod
    def import_ligne(filePath:str)->list:
        with open(filePath, "r", encoding="utf8") as file:
            paragraphs = file.read().split("\n\n")

        # Initialisation des arrets (juste le nom)
        arrets = [Stop(format_name(stop)) for stop in paragraphs[0].split(" N ")]

        # Ajout des trajets pour les deux sens
        # TODO : prendre en compte le sens retour + horaires weekend
        for paragraph in [paragraphs[1]]:
            horaires = [
                [
                    Horaire.from_scratch(horaire)
                    for horaire in ligne.split(" ")[1:]
                ]
                for ligne in paragraph.split("\n")
            ]
            # On transpose la "matrice" des horaires pour parcourir les colonnes
            horaires = list(zip(*horaires))
            arrets = Stop.add_horaires(horaires, arrets)
        return arrets

    @staticmethod
    def filterMany(stops:dict, horaire:Horaire)->dict:
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

if __name__ == "__main__":
    lignesFiles = [
        "data/test.txt",
        "data/1_Poisy-ParcDesGlaisins.txt",
        "data/2_Piscine-Patinoire_Campus.txt"
    ]

    stops = Stop.import_ligne(lignesFiles[1])
    print("Import terminé")
    stopsDico = {stop.name: stop for stop in stops}

    def displayBestPaths(departure:Stop, stopsDico:dict, horaires:list[Horaire]):
        for horaire in horaires:
            print("-----",horaire,"-----")
            stopsFiltered = Stop.filterMany(stopsDico, horaire)
            for arrival in stopsFiltered.values():
                try:
                    departure.display_best_paths(arrival.name, horaire)
                except NoPathException:
                    print(f"Il n'existe pas de chemin entre \"{departure.name}\" et \"{arrival.name}\" après {horaire}")
                finally:
                    print("Cache:", len(Stop.cache))
                    print("Trajet skippé avec le cache:", Stop.nbSkippedWithCache)
                    print()
            Stop.reset_cache()

    def displayStats(departure:Stop, stopsDico:dict, horaires:list[Horaire]):
        for horaire in horaires:
            print("-----",horaire,"-----")
            stopsDicoFiltered = Stop.filterMany(stopsDico, horaire)
            for arrival in stopsDicoFiltered.values():
                try:
                    timeTaken = timeit(lambda: departure.best_paths(arrival.name, horaire), number=1)
                    print(f"✔️Chemins entre \"{departure.name}\" et \"{arrival.name}\"")
                    print(f"Durée execution: {timeTaken:.2f}")
                except NoPathException:
                    print(f"❌   Pas de chemin entre \"{departure.name}\" et \"{arrival.name}\"")
                # finally:
                #     print("Cache:", len(Stop.cache))
                #     print("Trajet skippé avec le cache:", Stop.nbSkippedWithCache)
            Stop.reset_cache()

    departure:Stop = stopsDico["Lycée de poisy"]

    defaultHoraires = [Horaire(14, 30), Horaire(8, 30), Horaire(6, 30)]
    # displayBestPaths(departure, stopsDico, defaultHoraires)
    displayStats(departure, stopsDico, defaultHoraires)
    # departure.display_best_paths("3", Horaire(10))
