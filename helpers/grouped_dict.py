class GroupingDict(dict):
    def __init__(self, data, key_func):
        super().__init__()
        for item in data.values():
            key = key_func(item)
            if key not in self:
                self[key] = []
            self[key].append(item)

def main():
    class Person:
        def __init__(self, name, age, gender):
            self.name = name
            self.age = age
            self.gender = gender

        def age_group(self):
            if self.age < 13:
                return "kid"
            elif self.age < 20:
                return "teenager"
            elif self.age < 65:
                return "adult"
            else:
                return "senior"

        def __str__(self):
            return f"[{self.name}, ({self.age}, {self.gender})]"

        def __repr__(self):
            return str(self)

    person1 = Person("Alice",   5, "female")
    person2 = Person("Bob",     15, "male")
    person3 = Person("Charlie", 35, "male")
    person4 = Person("David",   18, "male")
    person5 = Person("Eve",     42, "female")

    d = {
        person1.name: person1,
        person2.name: person2,
        person3.name: person3,
        person4.name: person4,
        person5.name: person5,
    }

    by_age = GroupingDict(d, lambda p: p.age_group())
    adults = by_age["adult"]
    print(adults)

    by_sex = GroupingDict(d, lambda p: p.gender)
    print(by_sex["male"])


if __name__ == '__main__':
    main()
