

def format_name(name:str):
    return name.replace("_", " ").capitalize()

class Horaire:
    def __init__(self, hour:int, minute:int, day:int=0):
        self.day = day
        self.hour = hour
        self.minute = minute

    def duration(self, other):
        """Renvoie la durée entre deux horaires en minutes"""
        return (self.day - other.day) * 60 * 24 + (self.hour - other.hour) * 60 + self.minute - other.minute

    @staticmethod
    def from_scratch(text):
        if text == "-": return None
        return Horaire(*map(int, text.split(":")))

    def __lt__(self, other):
        return int(self.hour) < int(other.hour) or int(self.minute) < int(other.minute)

    def __sub__(self, other):
        return Horaire(self.hour-other.hour, self.minute-other.minute)

    def __str__(self):
        return f"{self.hour:02d}:{self.minute:02d}"

class NoPathException(Exception): pass

class Path:
    def __init__(self, departure:Horaire, stops:list, arrival:Horaire):
        self.departure = departure
        self.arrival = arrival
        self.stops = stops

    def is_shorter(self, other):
        if len(self.stops) == len(other.stops):
            return self.is_foremost(other)
        return len(self.stops) < len(other.stops)

    def is_faster(self, other):

        if self.duration() == other.duration():
            return self.is_foremost(other)
        return self.duration() < other.duration()

    def is_foremost(self, other):
        return self.arrival < other.arrival

    def duration(self):
        return self.arrival.duration(self.departure)

    def __str__(self):
        return f"({self.departure}) {' -> '.join(stop.__str__() for stop in self.stops)} ({self.arrival})"

class Stop:
    def __init__(self, name:str, neighbors:list=None):
        self.name = name
        self.neighbors = [] if neighbors is None else neighbors

    def paths(self, terminus:str, depart:Horaire, _explored:set=None):
        explored = set()
        explored.add(self.name)
        if _explored is not None: explored.update(_explored)
        paths = []
        if self.name == terminus: return [Path(depart, [self], depart)]
        for neighborDeparture, neighborArrival, neighbor in self.neighbors:
            # On skip le chemin si l'horaire est dépassé ou s'il a déjà été traversé
            if neighborDeparture < depart: continue
            if neighbor.name in explored: continue
            for path in neighbor.paths(terminus, neighborArrival, explored):
                paths.append(Path(neighborDeparture, self + path, path.arrival))
        return paths

    def best_paths(self, terminus:str, departure:Horaire):
        paths:list[Path] = self.paths(terminus, departure)
        if not paths: raise NoPathException
        foremost, shortest, fastest = paths[0], paths[0], paths[0]
        for path in paths[1:]:
            if path.is_shorter(shortest): shortest = path
            if path.is_faster(fastest): fastest = path
            if path.is_foremost(foremost): foremost = path
        return len(paths), foremost, shortest, fastest

    def display_best_paths(self, terminus:str, departure:Horaire):
        bestPaths = self.best_paths(terminus, departure)
        print(f"Voici les meilleurs trajets pour allez de {self.name} à {terminus} parmi {bestPaths[0]:_} trajets:")
        print(f"Foremost: {bestPaths[1]}, durée: {bestPaths[1].duration()}m")
        print(f"Shortest: {bestPaths[2]}, durée: {bestPaths[2].duration()}m")
        print(f"Fastest: {bestPaths[3]}, durée: {bestPaths[3].duration()}m")

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

    # arrival = stopsDico["Glaisin"]
    departure = stopsDico["Lycée de poisy"]
    horaire = Horaire(12,30)

    for arrival in stopsDico.values():
        try:
            departure.display_best_paths(arrival.name, horaire)
            print()
        except NoPathException as e:
            print(f"Il n'existe pas de chemin entre {departure.name} et {arrival.name} après {horaire})")