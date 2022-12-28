from unittest import TestCase

from game_engine.dice import _token_valence_and_value, Dice, Roll


class Test(TestCase):
    def test_token_valence_and_value(self):
        self.assertEqual(_token_valence_and_value("+81"), (1, "81"))
        self.assertEqual(_token_valence_and_value("-81"), (-1, "81"))
        self.assertEqual(_token_valence_and_value("- 81"), (-1, "81"))
        self.assertEqual(_token_valence_and_value("81"), (1, "81"))
        self.assertEqual(_token_valence_and_value("+ 8-1"), (1, "8-1"))
        self.assertEqual(_token_valence_and_value("+ - 81"), (-1, "81"))
        self.assertEqual(_token_valence_and_value(" - + 81"), (-1, "81"))
        self.assertEqual(_token_valence_and_value("--81"), (1, "81"))
        self.assertEqual(_token_valence_and_value("---81"), (-1, "81"))


class TestRoll(TestCase):
    def test_parse(self):
        parse = Roll.parse
        ast = self.assertEqual
        ast(str(parse("1d6 + 4d8+2d2 + 8")), "4D8 + 1D6 + 2D2 + 8")
        ast(str(parse("1d6 + 4d8 -2d2 + 8")), "4D8 + 1D6 - 2D2 + 8")
        ast(str(parse("1d6 + 4d8 -2d2 + -8")), "4D8 + 1D6 - 2D2 - 8")
        ast(str(parse("1d6 + 4d8 -2d2")), "4D8 + 1D6 - 2D2")
        ast(str(parse("1d6 + 9d2 -2d2")), "1D6 + 7D2")
        ast(str(parse("1d6 + 9d2 -2d2 + 8 -1")), "1D6 + 7D2 + 7")
        ast(str(parse("-1")), "- 1")

        # the d1 case (it came up)
        ast(str(parse("8d6 + 3d1 + 2")), "8D6 + 5")
        ast(str(parse("8d6 + 3d1 - 2")), "8D6 + 1")
        ast(str(parse("8d6 - 3d1 - 2")), "8D6 - 5")
        ast(str(parse("8d6 - 3d1 + 2")), "8D6 - 1")
        ast(str(parse("3d1")), "3")


class TestDice(TestCase):
    def test_dice(self):
        ast = self.assertEqual
        ast(Dice("1d6"), Dice(1, 6))

        dice = Dice("1d6")
        r = [dice.roll() for _ in range(1000)]
        ast(dice.min(), 1)
        ast(dice.max(), 6)
        ast(min(r), 1)
        ast(max(r), 6)

        # d1 means a constant
        ast(Dice("5d1").roll(), 5)
