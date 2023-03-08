from timeit import timeit

def format_name(name:str):
    """ Formate le nom d'un arrêt (ex. POISY_COLLÈGE -> Poisy collège)"""
    return name.replace("_", " ").capitalize()

class Schedule:
    """ Représente un horaire de bus """
    def __init__(self, hour:int=0, minute:int=0):
        self.hour = hour
        self.minute = minute

    def duration(self, other):
        """Renvoie la durée entre deux horaires en minutes"""
        return (self.hour - other.hour) * 60 + self.minute - other.minute

    @staticmethod
    def from_scratch(text):
        """ Renvoie un horaire normalisé à partir d'une donnée de fichier (ex. 5:58 | 7:05 | - | 8:00)"""
        if text == "-": return None
        return Schedule(*map(int, text.split(":")))

    def __lt__(self, other):
        return self.hour < other.hour or self.minute < other.minute

    def __sub__(self, other):
        return Schedule(self.hour - other.hour, self.minute - other.minute)

    def __str__(self):
        return f"{self.hour:02d}:{self.minute:02d}"

    def __repr__(self):
        return self.__class__.__name__ + f' {self.hour}:{self.minute}'

    def __bool__(self):
        return bool(self.hour or self.minute)

class NoPathException(Exception):
    """ Exception lancée quand il n'existe aucun trajet entre deux arrets """
    pass

class Path:
    """ Représente un trajet direct ou indirect entre deux arrêts """
    def __init__(self, departure:Schedule, stops:list, arrival:Schedule):
        self.departure = departure
        self.stops = stops
        self.arrival = arrival

    def is_shorter(self, other):
        """ Compare le nombre d'arrêts des trajets """
        if len(self.stops) == len(other.stops):
            return self.is_foremost(other)
        return len(self.stops) < len(other.stops)

    def is_faster(self, other):
        """ Compare la durée des trajets """
        if self.duration() == other.duration():
            return self.is_foremost(other)
        return self.duration() < other.duration()

    def is_foremost(self, other):
        """ Compare l'horaire d'arrivée des trajets """
        return self.arrival < other.arrival

    def duration(self):
        """ Calcul la durée entre le début et la fin du trajet """
        return self.arrival.duration(self.departure)

    def __str__(self):
        return f"({self.departure}) {' -> '.join(stop.__str__() for stop in self.stops)} ({self.arrival})"

class Stop:
    """ Représente un arrêt de bus """

    # Attributs statiques utilisés pour le système de cache
    cache:dict = dict()
    maxCache:int = 2048
    nbSkippedWithCache:int = 0

    def __init__(self, name:str, neighbors:list=None, neighborsWeekend:list=None):
        self.name = name
        self.neighbors = [] if neighbors is None else neighbors
        self.neighborsWeekend = [] if neighborsWeekend is None else neighborsWeekend

    def paths(self, terminus:str, departure:Schedule, weekend:bool=False, _explored:set=None):
        """ Méthode principale, renvoie l'ensemble des chemins possibles entre deux arrêts"""
        explored = set()
        explored.add(self.name)
        if _explored is not None: explored.update(_explored)

        paths = []
        if self.name == terminus: return [Path(departure, [self], departure)]

        cacheTuple = (self.name, terminus, departure)
        # On utilise le cache
        if cacheTuple in Stop.cache:
            Stop.nbSkippedWithCache += 1
            return Stop.cache[cacheTuple]

        # On choisit des voisins à parcourir en fonction du jour
        neighborsToSearch = self.neighborsWeekend if weekend else self.neighbors
        for neighborDeparture, neighborArrival, neighbor in neighborsToSearch:
            # On skip le chemin si l'horaire est dépassé
            if neighborDeparture < departure: continue
            # On le skip s'il a déjà été traversé
            if neighbor.name in explored: continue

            for path in neighbor.paths(terminus, neighborArrival, weekend, explored):
                newPath = Path(neighborDeparture, self + path, path.arrival)
                paths.append(newPath)

        if len(Stop.cache) < Stop.maxCache: Stop.cache[cacheTuple] = paths

        return paths

    def best_paths(self, terminus:str, departure:Schedule, weekend:bool=False):
        """ Calcule les meilleurs chemins renvoyés par la méthode paths """
        paths:list[Path] = self.paths(terminus, departure, weekend)
        if not paths: raise NoPathException(f"Il n'existe pas de chemin entre \"{self.name}\" et \"{terminus}\" après {departure}")
        foremost, shortest, fastest = paths[0], paths[0], paths[0]
        for path in paths[1:]:
            if path.is_shorter(shortest): shortest = path
            if path.is_faster(fastest): fastest = path
            if path.is_foremost(foremost): foremost = path
        return len(paths), foremost, shortest, fastest

    def display_best_paths(self, terminus:str, departure:Schedule=Schedule(), weekend:bool=False):
        """ Affiche les chemins renvoyés par la méthode best_paths """
        try:
            bestPaths = self.best_paths(terminus, departure, weekend)
            print(f'Voici les meilleurs trajets pour aller de \"{self.name}\" à \"{terminus}\"'
                  , f' à partir de {departure}' if departure else ''
                  , f' en weekend' if weekend else ''
                  , f', parmi {bestPaths[0]:_} trajets:'
                  , sep='')
            print(f"\tForemost: {bestPaths[1]}, durée: {bestPaths[1].duration()}m")
            print(f"\tShortest: {bestPaths[2]}, durée: {bestPaths[2].duration()}m")
            print(f"\tFastest: {bestPaths[3]}, durée: {bestPaths[3].duration()}m")
        except NoPathException as ex:
            print(ex)
        print()

    def filter(self, horaire: Schedule, weekend:bool=False):
        """ Retourne l'arrêt avec tous ses voisins accessibles à l'horaire donnée """
        neighborsToFilter = self.neighborsWeekend if weekend else self.neighbors
        return Stop(self.name, [
            neighbor
            for neighbor in neighborsToFilter
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
                    Schedule.from_scratch(horaire)
                    for horaire in ligne.split(" ")[1:]
                ]
                for ligne in paragraph.split("\n")
            ]

            # On transpose la "matrice" des horaires pour obtenir les colonnes
            horaireColumns = list(zip(*horaires))

            # Gestion différente selon chaque paragraphe
            if i == 0:
                network.addSchedules(horaireColumns, reverse=False, weekend=False)
            if i == 1:
                network.addSchedules(horaireColumns, reverse=True, weekend=False)
            if i == 2:
                network.addSchedules(horaireColumns, reverse=False, weekend=True)
            if i == 3:
                network.addSchedules(horaireColumns, reverse=True, weekend=True)
        return network

    def addSchedules(self, horaires: list[tuple], reverse:bool=False, weekend:bool = False):
        """ Ajoute des voisins aux différents arrêts (c'est un brainfuck, soyez prévenus) """
        for fuseau in horaires:
            oldArret, newArret, oldSchedule = None, None, None
            for iArret, horaire in enumerate(fuseau):
                # Cas de l'horaire vide "-"
                if horaire is None: continue
                newArret = self[-iArret if reverse else iArret]
                if oldArret is not None:
                    if weekend:
                        oldArret.neighborsWeekend.append((oldSchedule, horaire, newArret))
                    else:
                        oldArret.neighbors.append((oldSchedule, horaire, newArret))
                oldArret, oldSchedule = self[-iArret if reverse else iArret], horaire

    def filter(self, horaire: Schedule, weekend:bool=False):
        """ Retourne un réseau dont tout les arrets sont filtrés par horaire """
        return Network([stop.filter(horaire, weekend) for stop in self.stops])

    def __str__(self):
        return " | ".join(stop.name for stop in self.stops)


def displayBestPaths(departure:Stop, network:Network, horaires:list[Schedule], weekend:bool=False):
    """ Affiche les meilleurs chemins d'un arret à tout les autres, pour différents horaires """
    print("#####################################\n"
          "#               PATHS               #\n"
          "#####################################")
    for horaire in horaires:
        print("-----",horaire,"-----")
        stopsFiltered = network.filter(horaire, weekend)
        for stop in stopsFiltered:
            try:
                departure.display_best_paths(stop.name, horaire, weekend)
            except NoPathException as ex: print(ex)

def displayStats(departure:Stop, network:Network, horaires:list[Schedule], weekend:bool=False):
    """ Affiche les statistiques (durée, nombre de chemins, cache hits) lors du calcul de trajet d'un arret à tout les autres, pour différents horaires """
    print("#####################################\n"
          "#               STATS               #\n"
          "#####################################")
    for horaire in horaires:
        print("\n-----",horaire,"-----")
        for arrival in network.filter(horaire, weekend):
            try:
                timeTaken = timeit(lambda: departure.best_paths(arrival.name, horaire, weekend), number=1)
                print(f"✔️Chemins entre \"{departure.name}\" et \"{arrival.name}\"")
                print(f"Durée execution: {timeTaken:.2f}")
            except NoPathException:
                print(f"❌   Pas de chemin entre \"{departure.name}\" et \"{arrival.name}\"")
            finally:
                print("Cache hits:", Stop.nbSkippedWithCache)
        Stop.reset_cache()

if __name__ == "__main__":
    files = [
        "data/test_enonce.txt",
        "data/test.txt",
        "data/1_Poisy-ParcDesGlaisins.txt",
        "data/2_Piscine-Patinoire_Campus.txt"
    ]

    # ----- Import des réseaux -----
    # network = Network.parseFiles(files)
    network = Network.parseFile(files[1])
    print("Réseau importé: ", network, "\n")

    # ----- Calcul des trajets Pommaries -> Glaisin -----
    departure = network["Pommaries"]

    departure.display_best_paths("Glaisin")
    # departure.display_best_paths("Glaisin", departure=Schedule(6,30))
    # departure.display_best_paths("Glaisin", departure=Schedule(6,30), weekend=True)

    # defaultSchedules = [Schedule(14, 30), Schedule(8, 30), Schedule(6, 30)]

    # ------ Affichage spéciales : paths ------
    # displayBestPaths(departure, network, defaultSchedules, weekend=False)

    # ------ Affichage spéciales : stats ------
    # displayStats(departure, network, defaultSchedules)
