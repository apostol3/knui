from enum import Enum

__author__ = 'leon.ljsh'


class NeuronType(Enum):
    input = 0
    output = 1
    blank = 2
    active = 3
    limit = 4
    binary = 5
    gen = 6
    invert = 7


class Neuron:
    def __init__(self, id_, type_=NeuronType.blank, e_active=1, input_=None, output=None):
        self.id = id_
        self.type = type_
        self.energy = 0
        self.e_active = e_active
        self.input = input_ if input_ else []
        self.output = output if output else []


class Link:
    def __init__(self, id_, weight=1, input_=None, output=None):
        self.id = id_
        self.e_in = 0
        self.e_out = 0
        self.weight = weight
        self.input = input_
        self.output = output


class Visual:
    def __init__(self, id_, x=None, y=None, r=None):
        self.id = id_
        self.x = x
        self.y = y
        self.r = r

    def __str__(self):
        return 'Visual -- id: {}, x: {}, y: {}, r: {}'.format(self.id, self.x, self.y, self.r)


class Net:
    def __init__(self, name=None, note=None, id_=None, fitness=None):
        self.name = name
        self.note = note
        self.id = id_
        self.fitness = fitness
        self.neurons = []
        self.links = []
        self.visual = []

    def get_link(self, id_):
        for link in self.links:
            if link.id == id_:
                return link

    def get_neuron(self, id_):
        for neuron in self.neurons:
            if neuron.id == id_:
                return neuron

    def get_neuron_vis(self, id_):
        for n_v in self.visual:
            if n_v.id == id_:
                return n_v

    def delete_link(self, id_):
        link = self.get_link(id_)
        n_i = self.get_neuron(link.input)
        n_o = self.get_neuron(link.output)
        n_i.output.remove(id_)
        n_o.input.remove(id_)
        self.links.remove(link)

    def delete_neuron(self, id_):
        n = self.get_neuron(id_)
        links = []
        for link in n.input:
            links.append(link)
        for link in n.output:
            links.append(link)
        for link in links:
            self.delete_link(link)
        self.neurons.remove(n)

    def add_neuron(self, x, y):
        id_ = max(n.id for n in self.neurons) + 1
        self.neurons.append(Neuron(id_))
        self.visual.append(Visual(id_, x, y, 20))

    def add_link(self, id_from, id_to):
        if id_from == id_to:
            return
        n_from = self.get_neuron(id_from)
        n_to = self.get_neuron(id_to)
        links = [self.get_link(l) for l in n_from.output]
        links.extend([self.get_link(l) for l in n_to.input])
        for link in links:
            if link.input == id_from and link.output == id_to:
                return
        id_ = max(l.id for l in self.links) + 1 if len(self.links) else 1
        self.links.append(Link(id_, input_=id_from, output=id_to))
        n_from.output.append(id_)
        n_to.input.append(id_)

