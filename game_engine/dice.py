import random
from typing import List, Tuple, Any, Literal


class Dice:
    def __init__(self,
                 num_dice_or_expr: Literal[int, str] = None,
                 num_sides: int = None):
        if type(num_dice_or_expr) == str:
            dice = Dice.parse(num_dice_or_expr)
            self.num_dice = dice.num_dice
            self.num_sides = dice.num_sides
        else:
            num_dice = int(num_dice_or_expr)
            if num_dice < 1 or num_sides < 1:
                raise ValueError("Dice must be 1D1 or greater.")
            if num_dice > 5_000:
                raise ValueError("More than 5000 dice is not allowed.")
            self.num_dice = num_dice
            self.num_sides = num_sides

    def __eq__(self, other):
        return (self.num_dice, self.num_sides) == (other.num_dice, other.num_sides)

    @staticmethod
    def parse(txt: str):
        txt = txt.strip().replace(" ", "").lower()
        x, y = txt.split('d')
        x = 1 if x == '' else int(x)
        y = int(y)
        return Dice(x, y)

    def __str__(self):
        return f"{self.num_dice}D{self.num_sides}"

    def __repr__(self):
        return str(self)

    def roll(self):
        return sum([random.randint(1, self.num_sides) for _ in range(self.num_dice)])

    def min(self) -> int:
        return self.num_dice

    def max(self) -> int:
        return self.num_dice * self.num_sides

    def ave(self):
        return ((self.num_sides+1)/2) * self.num_dice


def _token_valence_and_value(token):
    valence = 1
    for i, c in enumerate(token):
        if c not in "+- ":
            break
        valence *= -1 if c == '-' else 1

    return valence, token[i:]


class Roll:
    def __init__(self, expr: str, dice: List[Tuple[int, Dice]] = None, constant=0):
        if expr is not None:
            roll = Roll.parse(str(expr))
            self._dice = roll._dice
            self.constant = roll.constant
        else:
            self._dice = dice
            self.constant = constant
            self._normalise()

    def _normalise(self):
        # create a sorted set of the types of dice present (if more than 1 sided)
        num_sides = sorted(list(set(d.num_sides for _, d in self._dice if d.num_sides > 1)), reverse=True)

        # for each type of dice present, tally the total
        num_dice = [sum([v*d.num_dice for v, d in self._dice if d.num_sides == ns]) for ns in num_sides]

        # get the 1 sided dice, and move them to the constant
        self.constant += sum([v * d.num_dice for v, d in self._dice if d.num_sides == 1])

        # rebuild the dice list
        self._dice = [(nd // abs(nd), Dice(abs(nd), ns)) for nd, ns in zip(num_dice, num_sides) if nd != 0]

    @staticmethod
    def parse(txt: str):
        """
        parses dice rolls eg: "1d6 + 4d8 -2d2 + 8"
        It's a bit of a hack and only supports addition/subtraction,
        but it passes a good set of unit tests
        """
        txt = txt.strip().replace(" ", "").lower()
        txt = txt.strip().replace("+-", "-")
        txt = txt.strip().replace("+", "!+")
        txt = txt.strip().replace("-", "!-")
        tokens = txt.split("!")
        tokens = [_token_valence_and_value(t) for t in tokens if len(t) > 1]
        dice = [(v, Dice.parse(t)) for v, t in tokens if 'd' in t]
        constant = sum([int(t)*v for v, t in tokens if 'd' not in t])
        return Roll(None, dice, constant)

    def __str__(self):
        expr = " ".join("++-"[v] + " " + str(d) for v, d in self._dice)
        if self.constant > 0:
            expr += " + " + str(abs(self.constant))
        if self.constant < 0:
            expr += " - " + str(abs(self.constant))

        return expr.strip("+ ")

    def __repr__(self):
        return str(self)

    def min(self) -> int:
        return sum([min(d.min()*v, d.max()*v) for v, d in self.dice]) + self.constant

    def max(self) -> int:
        return sum([max(d.min()*v, d.max()*v) for v, d in self.dice]) + self.constant

    def ave(self):
        return sum([d.ave()*v for v, d in self.dice]) + self.constant

    def roll(self):
        return sum([d.roll() * v for v, d in self.dice]) + self.constant

