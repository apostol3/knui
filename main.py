import json
import os

from kivy.adapters.listadapter import ListAdapter
from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.text import Label as CoreLabel
from kivy.garden.contextmenu import ContextMenu, ContextMenuTextItem
from kivy.graphics import Color, Rectangle, Ellipse, Mesh
from kivy.graphics import SmoothLine
from kivy.graphics import Translate, ScissorPush, ScissorPop, Scale
from kivy.lang import Builder
from kivy.properties import Property
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.label import Label
from kivy.uix.listview import ListItemButton
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol

from classes import *
from udp_stream import UdpStream

__author__ = "leon.ljsh"

ContextMenu, ContextMenuTextItem
Config.set('input', 'mouse', Config.get('input', 'mouse') + ',disable_multitouch')
nets = []


class ServerState(Enum):
    disconnected = 0
    stopped = 1
    running = 2
    paused = 3


neuron_colors = [
    (0.82, 1, 0.76), (0.6, 0.8, 0.4), (1, 1, 1), (0.6, 0.176, 0.07), (1, 0.51, 0.67), (0.8, 0.435, 0.345),
    (0.345, 0.8, 0.775), (0.33, 0.67, 1)]

neuron_labels = ["I", "O", " ", "A", "L", "B", "N", "G"]
neuron_names = ["input", "output", "blank", "activation", "limit", "binary", "inverter", "generator"]


class NetDrawer(Widget):
    def __init__(self, **kwargs):
        super(NetDrawer, self).__init__(**kwargs)
        self.bind(pos=self.draw)
        self.bind(size=self.draw)
        self.x0_pos = 0
        self.y0_pos = 0
        self.x1_pos = 0
        self.y1_pos = 0
        self.camx = 0
        self.camy = 0
        self.faulted_click = True
        self.neuron = None
        self.neuro_net = None
        self.link_with_neuron = None
        self.unlink_with_neuron = None

    def select_neuron(self, x, y):
        if self.neuro_net is None:
            return
        for n_v in self.neuro_net.visual[::-1]:
            if n_v.x - n_v.r < x < n_v.x + n_v.r and n_v.y - n_v.r < y < n_v.y + n_v.r:
                return self.neuro_net.get_neuron(n_v.id)

    def on_button_left_down(self, touch):
        self.x0_pos = touch.pos[0] - self.pos[0]
        self.y0_pos = -touch.pos[1] - self.pos[1] + self.size[1]
        self.neuron = self.select_neuron(self.x0_pos - self.camx, self.y0_pos - self.camy)
        self.draw()

    def on_button_left_move(self, touch):
        self.x1_pos = touch.pos[0] - self.pos[0]
        self.y1_pos = -touch.pos[1] - self.pos[1] + self.size[1]
        if self.neuron:
            n_v = self.neuro_net.get_neuron_vis(self.neuron.id)
            n_v.x += self.x1_pos - self.x0_pos
            n_v.y += self.y1_pos - self.y0_pos
        else:
            self.camx += self.x1_pos - self.x0_pos
            self.camy += self.y1_pos - self.y0_pos
        self.x0_pos = self.x1_pos
        self.y0_pos = self.y1_pos
        self.draw()

    def on_button_left_up(self, touch):
        self.x1_pos = touch.pos[0] - self.pos[0]
        self.y1_pos = -touch.pos[1] - self.pos[1] + self.size[1]
        if self.neuron:
            n_v = self.neuro_net.get_neuron_vis(self.neuron.id)
            n_v.x += self.x1_pos - self.x0_pos
            n_v.y += self.y1_pos - self.y0_pos
            if self.link_with_neuron:
                self.neuro_net.add_link(self.link_with_neuron, self.neuron.id)
                self.link_with_neuron = None
            elif self.unlink_with_neuron:
                n_in = self.neuro_net.get_neuron(self.unlink_with_neuron)
                for l_id in n_in.output:
                    link = self.neuro_net.get_link(l_id)
                    if link.output == self.neuron.id:
                        self.neuro_net.delete_link(l_id)
                        self.unlink_with_neuron = None
                        break
        else:
            self.camx += self.x1_pos - self.x0_pos
            self.camy += self.y1_pos - self.y0_pos
        self.draw()

    def on_button_right_up(self, touch):
        if self.neuro_net is None:
            return
        if self.neuron:
            app.root.ids.context_on_neuron.show(*touch.pos)
        else:
            app.root.ids.context_on_drawbox.show(*touch.pos)

    def on_button_right_down(self, touch):
        self.on_button_left_down(touch)

    def on_touch_down(self, touch):
        if not (self.pos[0] < touch.pos[0] < self.pos[0] + self.size[0] and
                            self.pos[1] < touch.pos[1] < self.pos[1] + self.size[1]):
            return
        self.faulted_click = False
        if touch.button == 'left':
            self.on_button_left_down(touch)
        elif touch.button == 'right':
            self.on_button_right_down(touch)

    def on_touch_up(self, touch):
        if self.faulted_click:
            return
        if touch.button == 'left':
            self.on_button_left_up(touch)
        elif touch.button == 'right':
            self.on_button_right_up(touch)

        self.faulted_click = True

    def on_touch_move(self, touch):
        if self.faulted_click:
            return
        if touch.button == 'left':
            self.on_button_left_move(touch)

    def draw(self, *_):
        self.canvas.clear()

        with self.canvas:
            ScissorPush(x=self.pos[0], y=self.pos[1], width=self.size[0], height=self.size[1])
            Color(1, 1, 1)
            Translate(self.pos[0], self.pos[1] + self.size[1])
            Scale(1, -1, 1)
            Rectangle(pos=(0, 0), size=self.size)
            Translate(self.camx, self.camy)
            self.inner_draw()
            Translate(-self.camx, -self.camy)
            Color(1, 0, 0, 0.5)
            Ellipse(pos=(self.x0_pos - 5, self.y0_pos - 5), size=(10, 10))
            Color(1, 0, 1, 0.5)
            Ellipse(pos=(self.x1_pos - 15 / 2, self.y1_pos - 15 / 2), size=(15, 15))
            Color(0, 0, 0)
            if self.neuro_net:
                label = CoreLabel(text='ID: {}\nName: {}\nNeurons: {}\nLinks: {}\nNote: {}'
                                  .format(self.neuro_net.id, self.neuro_net.name, len(self.neuro_net.neurons),
                                          len(self.neuro_net.links), self.neuro_net.note),
                                  font_size=12, halign='left')
                label.refresh()
                text = label.texture
                self.canvas.add(
                    Rectangle(size=(text.size[0], -text.size[1]),
                              pos=(0, self.size[1]),
                              texture=text))
            if self.neuron:
                label = CoreLabel(text='ID: {}\nType: {}\nActivation: {}\nEnergy: {}\nInputs: {}\nOutputs: {}'
                                  .format(self.neuron.id, neuron_names[self.neuron.type.value],
                                          self.neuron.e_active, self.neuron.energy, len(self.neuron.input),
                                          len(self.neuron.output)),
                                  font_size=12, halign='right')
                label.refresh()
                text = label.texture
                self.canvas.add(
                    Rectangle(size=(text.size[0], -text.size[1]),
                              pos=(self.size[0] - text.size[0], self.size[1]),
                              texture=text))
            Scale(1, -1, 1)
            Translate(-self.pos[0], -self.pos[1] - self.size[1])

            ScissorPop()

    def inner_draw(self, *_):
        Color(0, 0, 0)
        if self.neuro_net is None:
            return

        Color(0, 0, 0, 0.8)
        for link in self.neuro_net.links:
            n_in = self.neuro_net.get_neuron_vis(link.input)
            n_out = self.neuro_net.get_neuron_vis(link.output)

            if not (n_in and n_out):
                continue

            v_x = n_out.x - n_in.x
            v_y = n_out.y - n_in.y
            d = (v_x ** 2 + v_y ** 2) ** 0.5

            if d < n_out.r + n_in.r:
                continue

            vn_x = v_x / d
            vn_y = v_y / d

            arr_size_x = 6
            arr_size_y = 6
            arr_inner = 4
            finish_x = n_out.x - vn_x * n_out.r
            finish_y = n_out.y - vn_y * n_out.r
            SmoothLine(points=(n_in.x + vn_x * n_out.r, n_in.y + vn_y * n_out.r, finish_x - vn_x * arr_inner,
                               finish_y - vn_y * arr_inner), width=1)
            Mesh(vertices=(finish_x, finish_y, 0, 0,
                           finish_x - vn_x * arr_size_y - vn_y * arr_size_x,
                           finish_y - vn_y * arr_size_y + vn_x * arr_size_x, 0, 0,
                           finish_x - vn_x * arr_inner,
                           finish_y - vn_y * arr_inner, 0, 0,
                           finish_x - vn_x * arr_size_y + vn_y * arr_size_x,
                           finish_y - vn_y * arr_size_y - vn_x * arr_size_x, 0, 0),
                 indices=(0, 1, 2, 3),
                 mode='triangle_fan')

        for neuron in self.neuro_net.neurons:
            n_v = self.neuro_net.get_neuron_vis(neuron.id)
            cf = neuron.energy / neuron.e_active if neuron.e_active != 0 else 0
            cf = max(min(cf, 1), 0)
            angle_start = 180 - cf * 360
            l_width = 1.3 if cf == 1 else 1.1

            l_color = (0.6, 0.2, 0.2) if cf < 1 else (1, 0.2, 0.2)

            Color(*neuron_colors[neuron.type.value])
            Ellipse(pos=(n_v.x - n_v.r, n_v.y - n_v.r), size=(n_v.r * 2, n_v.r * 2))

            Color(0, 0, 0)
            SmoothLine(ellipse=(n_v.x - n_v.r, n_v.y - n_v.r, n_v.r * 2, n_v.r * 2),
                       width=1.05)

            Color(*l_color)
            SmoothLine(ellipse=(n_v.x - n_v.r, n_v.y - n_v.r, n_v.r * 2, n_v.r * 2, angle_start, 180),
                       width=l_width)

            if self.neuron and neuron.id == self.neuron.id:
                Color(0.7, 0, 0.8)
                SmoothLine(ellipse=(n_v.x - n_v.r, n_v.y - n_v.r, n_v.r * 2, n_v.r * 2), width=2)

            Color(0, 0, 0)
            label = CoreLabel(text='{0}\n{1:.3}'.format(neuron_labels[neuron.type.value], float(neuron.e_active)),
                              font_size=12, halign='center')
            label.refresh()
            text = label.texture
            self.canvas.add(
                Rectangle(size=(text.size[0], -text.size[1]),
                          pos=(round(n_v.x - text.size[0] / 2), round(n_v.y + text.size[1] / 2)),
                          texture=text))

    def set_neuron_type(self, type_):
        if self.neuron is None:
            return
        self.neuron.type = NeuronType(type_)
        app.root.ids.context_on_neuron.hide()
        self.draw()

    def delete_neuron(self):
        self.neuro_net.delete_neuron(self.neuron.id)
        app.root.ids.context_on_neuron.hide()
        self.draw()

    def unlink_all(self):
        if self.neuro_net is None or self.neuron is None:
            return

        links = []
        for link in self.neuron.input:
            links.append(link)
        for link in self.neuron.output:
            links.append(link)
        for link in links:
            self.neuro_net.delete_link(link)
        app.root.ids.context_on_neuron.hide()
        self.draw()

    def add_neuron(self):
        self.neuro_net.add_neuron(self.x0_pos - self.camx, self.y0_pos - self.camy)
        app.root.ids.context_on_drawbox.hide()
        self.draw()

    def on_link_with(self):
        self.link_with_neuron = self.neuron.id
        app.root.ids.context_on_neuron.hide()

    def on_unlink_with(self):
        self.unlink_with_neuron = self.neuron.id
        app.root.ids.context_on_neuron.hide()


def auto_pos(neuro_net):
    if neuro_net is None:
        raise TypeError()

    dt = 0.1
    r = 20
    maxx = app.drawbox.size[0]
    maxy = app.drawbox.size[1]

    for nr in neuro_net.neurons:
        vr = neuro_net.get_neuron_vis(nr.id)
        force = (0, 0)
        if nr.type == NeuronType.input or nr.type == NeuronType.output:
            continue
        for o_id in nr.output:
            o_l = neuro_net.get_link(o_id)
            o_vr = neuro_net.get_neuron_vis(o_l.output)
            dif = (o_vr.x - vr.x, o_vr.y - vr.y)
            dif_d = (dif[0] ** 2 + dif[1] ** 2) ** 0.5
            if dif_d > r * 5:
                dif = (dif[0] * (1 - 1 / dif_d), dif[1] * (1 - 1 / dif_d))
            force = (force[0] + dif[0], force[1] + dif[1])

        for i_id in nr.input:
            i_l = neuro_net.get_link(i_id)
            i_vr = neuro_net.get_neuron_vis(i_l.input)
            dif = (i_vr.x - vr.x, i_vr.y - vr.y)
            dif_d = (dif[0] ** 2 + dif[1] ** 2) ** 0.5
            if dif_d > r * 5:
                dif = (dif[0] * (1 - 1 / dif_d), dif[1] * (1 - 1 / dif_d))
            force = (force[0] + dif[0], force[1] + dif[1])

        for n_nr in neuro_net.neurons:
            if n_nr.id == nr.id:
                continue
            n_vr = neuro_net.get_neuron_vis(n_nr.id)
            dif = (n_vr.x - vr.x, n_vr.y - vr.y)
            dif_d = (dif[0] ** 2 + dif[1] ** 2) ** 0.5
            if dif_d < r * 10 and dif_d != 0:
                force = (force[0] + dif[0] * (1 - r * 10 / dif_d), force[1] + dif[1] * (1 - r * 10 / dif_d))

        vr.x, vr.y = (vr.x + force[0] * dt, vr.y + force[1] * dt)
        vr.x = max(min(vr.x, maxx - vr.r), vr.r)
        vr.y = max(min(vr.y, maxy - vr.r), vr.r)


def load_net_from_dict(doc):
    net = Net()
    net.name = doc['name']
    net.note = doc['note']
    net.id = doc['id']
    net.fitness = doc['fitness']
    net.visual = [Visual(i['id'], i['x'], i['y'], i['r']) for i in doc['visual']['neurons']]
    net.neurons = [Neuron(i['id'], NeuronType(i['type']), i['e_active'], i['in'], i['out'])
                   for i in doc['neurons']]
    net.links = [Link(i['id'], i['weight'], i['in'], i['out']) for i in doc['links']]
    return net


def open_file(path):
    global app
    f = open(path, 'r')
    doc = json.load(f)
    f.close()
    nets.append(load_net_from_dict(doc))
    app.update_list()


def save_file(path, net):
    if net is None:
        raise TypeError()
    filename = open(path, "w")
    doc = {'name': net.name, 'note': net.note, 'id': net.id, 'fitness': net.fitness, 'neurons': []}

    for nr in net.neurons:
        doc_nr = {'id': nr.id, 'energy': nr.energy, 'e_active': nr.e_active, 'type': nr.type.value, 'in': nr.input,
                  'out': nr.output}
        doc['neurons'].append(doc_nr)

    doc['links'] = []
    for link in net.links:
        doc_link = {'id': link.id, 'in': link.input, 'out': link.output, 'weight': link.weight, 'e_in': link.e_in,
                    'e_out': link.e_out}
        doc['links'].append(doc_link)

    doc['visual'] = {"neurons": []}

    for vis in net.visual:
        doc_nr = {'id': vis.id, 'x': vis.x, 'y': vis.y, 'r': vis.r}
        doc['visual']['neurons'].append(doc_nr)

    out_inf = json.dumps(doc, indent=4)
    filename.write(out_inf)
    filename.close()


class MainWindow(App):
    state = Property(ServerState.disconnected)

    def __init__(self, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        self.stream = None
        self.rpc = None

    def build(self):
        self.neuron_names = neuron_names
        self.update_text = ['∞', 'low', 'mid', 'high']

        def list_item_args_converter(row_index, obj):
            return {'text': '%d:%d' % (row_index, obj.fitness),
                    'size_hint_y': None,
                    'height': 25}

        self.list_adapter = ListAdapter(data=nets, args_converter=list_item_args_converter,
                                        cls=ListItemButton, selection_mode='single')

        self.list_adapter.bind(on_selection_change=self.update_select)
        self.root = Builder.load_file('main_window.kv')
        self.drawbox = self.root.ids.drawbox

        open_file("to.nnt")
        return self.root

    def update_list(self):
        old_sel = self.list_adapter.selection
        app.list_adapter.data = nets
        if len(old_sel) and old_sel[0].index < len(nets):
            self.list_adapter.select_item_view(self.list_adapter.get_view(old_sel[0].index))
            self.update_select()

    def update_select(self, *_):
        if len(self.list_adapter.selection) == 0:
            self.drawbox.neuro_net = None
        else:
            self.drawbox.neuro_net = nets[self.list_adapter.selection[0].index]

        self.drawbox.neuron = None
        self.drawbox.link_with_neuron = None
        self.drawbox.unlink_with_neuron = None
        self.drawbox.camx = 0
        self.drawbox.camy = 0
        self.drawbox.draw()

    def on_btn_connect(self, *_):
        if self.state != ServerState.disconnected:
            self.state = ServerState.disconnected
            self.stream.disconnect()
            self.stream = None
            self.rpc = None
        else:
            self.stream = UdpStream(app.root.ids.inp_ip.text, int(app.root.ids.inp_host.text), 1000)
            self.stream.connect()
            self.rpc = JSONRPCProtocol()
            self.state = ServerState.stopped
            self.server_get_state()

    def send_request(self, request):
        req = request.serialize()
        print("send request: {}, args: {}".format(request.method, request.args))
        self.stream.send(bytes(req + "\0", encoding='utf8'))
        raw_rep = self.stream.receive()
        rep = self.rpc.parse_reply(raw_rep.decode().strip("\0 "))
        if hasattr(rep, "error"):
            print("get error: " + rep.error)
        else:
            print("get response: {0}".format(rep.result if len(raw_rep) < 255 else "<too long to print>"))
        return rep

    def server_command(self):
        if self.state == ServerState.running:
            self.server_pause()
        elif self.state == ServerState.stopped:
            self.server_start()
        elif self.state == ServerState.paused:
            self.server_resume()

    def server_stop(self):
        rep = self.send_request(self.rpc.create_request("stop"))
        if hasattr(rep, "error"):
            return

        self.state = ServerState.stopped

    def server_pause(self):
        rep = self.send_request(self.rpc.create_request("pause"))
        if hasattr(rep, "error"):
            return

        self.state = ServerState.paused

    def server_resume(self):
        rep = self.send_request(self.rpc.create_request("resume"))
        if hasattr(rep, "error"):
            return
        self.state = ServerState.running

    def server_start(self):
        if self.state == ServerState.paused:
            rep = self.send_request(self.rpc.create_request("resume"))
            if hasattr(rep, "error"):
                return
            self.state = ServerState.running
        elif self.state == ServerState.stopped:
            rep = self.send_request(
                self.rpc.create_request("start", kwargs={'rounds': int(self.root.ids.inp_rounds.text),
                                                         'popsize': int(self.root.ids.inp_pop.text)}))
            if hasattr(rep, "error"):
                return
            self.state = ServerState.running

    def bind_get_pop(self):
        print("on slider up")
        delay = [0, 3, 1, 0.3]
        self.server_get_pop()
        if int(app.root.ids.update_slider.value) != 0:
            Clock.unschedule(self.server_get_pop)
            Clock.schedule_interval(self.server_get_pop, delay[int(app.root.ids.update_slider.value)])
        else:
            Clock.unschedule(self.server_get_pop)

    def server_get_pop(self, *_):
        global nets

        if self.state == ServerState.disconnected:
            return

        rep = self.send_request(self.rpc.create_request("get_population"))
        if hasattr(rep, 'error'):
            return
        doc = rep.result
        nets = [load_net_from_dict(net) for net in doc["nets"]]
        self.update_list()

    def server_get_state(self):
        if self.state == ServerState.disconnected:
            return

        rep = self.send_request(self.rpc.create_request("get_state"))

        if hasattr(rep, 'error'):
            return

        doc = rep.result
        state_info = doc["state"]
        if state_info == 'running':
            self.state = ServerState.running
        elif state_info == 'paused':
            self.state = ServerState.paused
        elif state_info == 'stopped':
            self.state = ServerState.stopped

        self.root.ids.inp_rounds.text = str(doc['max_round'])
        self.root.ids.inp_pop.text = str(doc['popsize'])

    def on_pass(self, *_):
        pass

    def on_auto_pos(self, *_):
        if self.drawbox.neuro_net is None:
            return
        auto_pos(self.drawbox.neuro_net)

        self.drawbox.draw()

    def save_file_dialog(self, *_):
        p = Popup(title='Save net', size_hint=(.9, .9))
        b = BoxLayout(orientation='vertical')
        cur_path = Label(size_hint_y=None, height='30dp')
        b.add_widget(cur_path)
        f = FileChooserIconView(path='.', size_hint=(1, 1))

        f.filters = ["*.nnt"]

        def selection_cb(*_):
            file_input.text = os.path.basename(f.selection[0])

        def choose_cb(*_):
            file_input.text = os.path.basename(f.selection[0])
            final_save()

        def final_save(*_):
            fname = file_input.text + ('.nnt' if file_input.text.find('.') == -1 else '')
            if os.path.exists(fname):
                bv_over_label.text = 'File "{}" already exists\nOverwrite it?'.format(fname)
                p_over.open()
                return

            p.dismiss()
            save_file(os.path.join(f.path, fname), self.drawbox.neuro_net)

        def change_path(*_):
            cur_path.text = os.path.abspath(f.path) + os.path.sep

        def cancel_callback(*_):
            p.dismiss()

        f.bind(on_submit=choose_cb)
        f.bind(selection=selection_cb)
        f.bind(path=change_path)
        change_path()
        b.add_widget(f)

        b2 = BoxLayout(orientation='horizontal', height='30dp', size_hint_y=None, spacing=10)
        label = Label(text='File:', width='50dp', size_hint_x=None)
        file_input = TextInput(multiline=False)
        btn_ok = Button(text='Ok', size_hint_x=None, on_release=final_save)

        btn_cancel = Button(text='Cancel', size_hint_x=None, on_release=cancel_callback)

        b2.add_widget(label)
        b2.add_widget(file_input)
        b2.add_widget(btn_ok)
        b2.add_widget(btn_cancel)

        b.add_widget(b2)
        p.add_widget(b)

        def b_over_ok_cb(*_):
            p_over.dismiss()
            p.dismiss()
            fname = file_input.text + ('.nnt' if file_input.text.find('.') == -1 else '')
            save_file(os.path.join(f.path, fname), self.drawbox.neuro_net)

        def b_over_no_cb(*_):
            p_over.dismiss()

        p_over = Popup(title='Warning', height="200dp", width="300dp", size_hint=(None, None))
        bv_over = BoxLayout(orientation='vertical')
        bv_over_label = Label(halign='center')
        bv_over.add_widget(bv_over_label)
        bh_over = BoxLayout(orientation='horizontal', size_hint=(1, None), height="35dp")
        b_over_ok = Button(text='Ok')
        b_over_ok.bind(on_release=b_over_ok_cb)
        bh_over.add_widget(b_over_ok)
        b_over_no = Button(text='Cancel')
        b_over_no.bind(on_release=b_over_no_cb)
        bh_over.add_widget(b_over_no)
        bv_over.add_widget(bh_over)
        p_over.add_widget(bv_over)
        p.open()

    def open_file_dialog(self, *_):
        p = Popup(title='Open net', size_hint=(.9, .9))
        b = BoxLayout(orientation='vertical')
        cur_path = Label(size_hint_y=None, height='30dp')
        b.add_widget(cur_path)
        f = FileChooserIconView(path='.', size_hint=(1, 1))

        f.filters = ["*.nnt"]

        def selection_cb(*_):
            file_input.text = os.path.basename(f.selection[0])

        def choose_cb(*_):
            file_input.text = os.path.basename(f.selection[0])
            final_open()

        def final_open(*_):
            p.dismiss()
            open_file(os.path.join(f.path, file_input.text))

        def change_path(*_):
            cur_path.text = os.path.abspath(f.path) + os.path.sep

        def cancel_callback(*_):
            p.dismiss()

        f.bind(on_submit=choose_cb)
        f.bind(selection=selection_cb)
        f.bind(path=change_path)
        change_path()
        b.add_widget(f)

        b2 = BoxLayout(orientation='horizontal', height='30dp', size_hint_y=None, spacing=10)
        label = Label(text='File:', width='50dp', size_hint_x=None)
        file_input = TextInput(multiline=False)
        btn_ok = Button(text='Ok', size_hint_x=None)
        btn_ok.bind(on_release=final_open)

        btn_cancel = Button(text='Cancel', size_hint_x=None)

        btn_cancel.bind(on_release=cancel_callback)

        b2.add_widget(label)
        b2.add_widget(file_input)
        b2.add_widget(btn_ok)
        b2.add_widget(btn_cancel)

        b.add_widget(b2)
        p.add_widget(b)
        p.open()


app = MainWindow()
app.run()
