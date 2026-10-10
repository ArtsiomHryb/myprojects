import pygame, math, random

pygame.init()
W, H = 1000, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Космический корабль")
clock = pygame.time.Clock()
FPS = 60

BLACK  = (2, 3, 12)
WHITE  = (245, 250, 255)
CYAN   = (0, 220, 240)
YELLOW = (255, 220, 80)
ORANGE = (255, 140, 0)
RED    = (235, 70, 70)
GREEN  = (100, 230, 140)
GREY   = (150, 155, 175)
DIM    = (80, 90, 110)
PANEL  = (10, 15, 32)
BORDER = (60, 95, 150)
BLUE_C = (60, 130, 240)
RED_C  = (240, 80, 80)

SLICE_W = 25.0
SHIP_LIMIT_X = 550.0
SHIP_LIMIT_Y = 390.0


class V4:
    __slots__ = ('x','y','z','w')
    def __init__(s, x=0.0, y=0.0, z=0.0, w=0.0):
        s.x, s.y, s.z, s.w = float(x), float(y), float(z), float(w)
    def __add__(s,o): return V4(s.x+o.x, s.y+o.y, s.z+o.z, s.w+o.w)
    def __sub__(s,o): return V4(s.x-o.x, s.y-o.y, s.z-o.z, s.w-o.w)
    def __mul__(s,k): return V4(s.x*k, s.y*k, s.z*k, s.w*k)
    __rmul__ = __mul__

def rot4(v, a, plane):
    c, s = math.cos(a), math.sin(a)
    x, y, z, w = v.x, v.y, v.z, v.w
    if plane == 'XY': return V4(x*c-y*s, x*s+y*c, z, w)
    if plane == 'XZ': return V4(x*c-z*s, y, x*s+z*c, w)
    if plane == 'XW': return V4(x*c-w*s, y, z, x*s+w*c)
    if plane == 'YZ': return V4(x, y*c-z*s, y*s+z*c, w)
    if plane == 'YW': return V4(x, y*c-w*s, z, y*s+w*c)
    return V4(x, y, z*c-w*s, z*s+w*c)

FOV_3D = 620.0
CAM_Z  = 700.0

def proj(x, y, z):
    rz = z + CAM_Z
    if rz < 60: return None
    k = FOV_3D / rz
    return (W/2 + x*k, H/2 + y*k, k, rz)

def w_color(base, w):
    t = min(1.0, abs(w)/180.0) * 0.85
    tgt = BLUE_C if w < 0 else RED_C
    return (int(base[0]*(1-t) + tgt[0]*t),
            int(base[1]*(1-t) + tgt[1]*t),
            int(base[2]*(1-t) + tgt[2]*t))

_glow = {}
def get_glow(color, radius):
    if radius < 1: return None
    key = (color[0]//16, color[1]//16, color[2]//16, radius//4)
    if key in _glow: return _glow[key]
    size = radius * 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    steps = max(4, min(12, radius//4))
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        a = int(90 * (1 - i/steps)**2)
        if a > 0 and r > 0:
            pygame.draw.circle(s, (color[0], color[1], color[2], a),
                               (radius, radius), r)
    if len(_glow) < 300: _glow[key] = s
    return s

ROCK_PALETTES = {
    'gray': {
        'shades': [(175, 175, 178), (140, 140, 143),
                   (110, 110, 113), (160, 160, 163)],
        'specular': 0.12,
    },
    'dark_gray': {
        'shades': [(105, 105, 110), (80, 80, 85),
                   (55, 55, 60), (95, 95, 100)],
        'specular': 0.15,
    },
    'metallic': {
        'shades': [(200, 205, 215), (165, 170, 180),
                   (105, 110, 120), (180, 185, 195)],
        'specular': 0.40,
    },
    'carbon': {
        'shades': [(72, 75, 82), (52, 54, 60),
                   (30, 32, 38), (62, 65, 72)],
        'specular': 0.08,
    },
}

def make_rock_mesh(size, seed, n_ring, m_rings, irregularity):
    """
    Низкополигональный камень.
    - n_ring: вершин в кольце
    - m_rings: количество колец по вертикали
    - irregularity: разброс вершин
    - некоторые вершины вдавлены внутрь (сколы)
    """
    rnd = random.Random(seed)
    # Северный полюс
    verts = [(0, size * rnd.uniform(0.9, 1.15), 0)]
    rings = []
    for m in range(1, m_rings):
        phi = math.pi * m / m_rings
        y = size * math.cos(phi)
        r = size * math.sin(phi)
        ring = []
        for n in range(n_ring):
            theta = math.tau * n / n_ring
            rr = r * rnd.uniform(1 - irregularity, 1 + irregularity)
            yy = y * rnd.uniform(1 - irregularity * 0.5,
                                 1 + irregularity * 0.5)
            # Скол: 12% вершин вдавлены внутрь
            if rnd.random() < 0.12:
                rr *= rnd.uniform(0.55, 0.75)
            # Выступ: 8% вершин выпирают
            elif rnd.random() < 0.08:
                rr *= rnd.uniform(1.15, 1.35)
            ring.append(len(verts))
            verts.append((rr * math.cos(theta), yy, rr * math.sin(theta)))
        rings.append(ring)
    # Южный полюс
    verts.append((0, -size * rnd.uniform(0.85, 1.15), 0))
    south = len(verts) - 1
    # Грани
    faces = []
    for n in range(n_ring):
        faces.append([0, rings[0][(n+1) % n_ring], rings[0][n]])
    for m in range(len(rings)-1):
        for n in range(n_ring):
            a = rings[m][n]; b = rings[m][(n+1) % n_ring]
            c = rings[m+1][(n+1) % n_ring]; d = rings[m+1][n]
            faces.append([a, b, c, d])
    for n in range(n_ring):
        faces.append([south, rings[-1][n], rings[-1][(n+1) % n_ring]])
    return verts, faces

class Asteroid:
    KINDS = {
        'meteorite': {
            'size': (12, 22),
            'n_ring': 6, 'm_rings': 3, 'irregularity': 0.42,
            'hp': 1,
            'speed': (280, 380),
            'palettes': ['gray', 'dark_gray', 'carbon', 'metallic'],
            'craters': (2, 4),
            'scratches': (1, 3),
            'spawn_weight': 6,
        },
        'asteroid': {
            'size': (24, 44),
            'n_ring': 8, 'm_rings': 4, 'irregularity': 0.33,
            'hp': 2,
            'speed': (180, 260),
            'palettes': ['gray', 'dark_gray', 'metallic'],
            'craters': (5, 8),
            'scratches': (3, 5),
            'spawn_weight': 3,
        },
        'large': {
            'size': (50, 78),
            'n_ring': 10, 'm_rings': 5, 'irregularity': 0.24,
            'hp': 3,
            'speed': (120, 180),
            'palettes': ['gray', 'dark_gray', 'metallic'],
            'craters': (8, 12),
            'scratches': (4, 7),
            'spawn_weight': 1,
        },
    }

    def __init__(self, pos, seed, kind=None):
        if kind is None:
            kinds = list(self.KINDS.keys())
            weights = [self.KINDS[k]['spawn_weight'] for k in kinds]
            kind = random.choices(kinds, weights=weights)[0]
        self.kind = kind
        cfg = self.KINDS[kind]
        rnd = random.Random(seed)
        self.seed = seed

        # Размер и форма
        size = rnd.uniform(*cfg['size'])
        self.scale = size
        self.verts, self.faces = make_rock_mesh(
            size, seed, cfg['n_ring'], cfg['m_rings'], cfg['irregularity'])

        # HP
        self.hp = cfg['hp']
        self.max_hp = cfg['hp']
        self.hit_flash = 0.0

        # Палитра
        pal_name = rnd.choice(cfg['palettes'])
        self.palette_name = pal_name
        pal = ROCK_PALETTES[pal_name]
        self.specular = pal['specular']
        # Цвет каждой грани — случайный из палитры
        self.face_colors = [rnd.choice(pal['shades'])
                            for _ in self.faces]

        # Кратеры — затемнённые грани
        n_craters = rnd.randint(*cfg['craters'])
        self.crater_faces = {}
        for _ in range(n_craters):
            fi = rnd.randrange(len(self.faces))
            self.crater_faces[fi] = rnd.uniform(0.45, 0.68)

        # Царапины — отрезки на поверхности в локальных координатах
        n_scr = rnd.randint(*cfg['scratches'])
        self.scratches = []
        for _ in range(n_scr):
            theta = rnd.uniform(0, math.tau)
            phi = rnd.uniform(0.35, math.pi * 0.65)
            r = size * 0.95
            x1 = r * math.sin(phi) * math.cos(theta)
            y1 = r * math.cos(phi)
            z1 = r * math.sin(phi) * math.sin(theta)
            dth = rnd.uniform(-0.85, 0.85)
            dph = rnd.uniform(-0.55, 0.55)
            x2 = r * math.sin(phi+dph) * math.cos(theta+dth)
            y2 = r * math.cos(phi+dph)
            z2 = r * math.sin(phi+dph) * math.sin(theta+dth)
            self.scratches.append(((x1,y1,z1), (x2,y2,z2)))

        # Позиция и вращение
        self.pos = pos
        self.rx = rnd.uniform(0, math.tau)
        self.ry = rnd.uniform(0, math.tau)
        self.rz = rnd.uniform(0, math.tau)
        self.rvx = rnd.uniform(-0.4, 0.4)
        self.rvy = rnd.uniform(-0.4, 0.4)
        self.rvz = rnd.uniform(-0.4, 0.4)
        sp = rnd.uniform(*cfg['speed'])
        self.vel = V4(rnd.uniform(-50, 50), rnd.uniform(-50, 50),
                      -sp, rnd.uniform(-30, 30))
        self.radius = size * 1.3
        self.alive = True

    def rotate_vertex(self, v):
        x, y, z = v
        cx, sx = math.cos(self.rx), math.sin(self.rx)
        y1 = y*cx - z*sx; z1 = y*sx + z*cx; x1 = x
        cy, sy = math.cos(self.ry), math.sin(self.ry)
        x2 = x1*cy + z1*sy; z2 = -x1*sy + z1*cy; y2 = y1
        cz, sz = math.cos(self.rz), math.sin(self.rz)
        x3 = x2*cz - y2*sz; y3 = x2*sz + y2*cz; z3 = z2
        return (x3, y3, z3)

    def update(self, dt, ship):
        # Легкое наведение на игрока
        if random.random() < 0.02:
            dx = ship.x - self.pos.x
            dy = ship.y - self.pos.y
            L = math.hypot(dx, dy) + 1e-6
            self.vel.x += (dx/L) * 60 * dt
            self.vel.y += (dy/L) * 60 * dt
        self.pos = self.pos + self.vel * dt
        self.rx += self.rvx * dt
        self.ry += self.rvy * dt
        self.rz += self.rvz * dt
        if self.hit_flash > 0:
            self.hit_flash = max(0, self.hit_flash - dt * 3)
        if self.pos.z < -600 or self.pos.z > 4200: self.alive = False
        if abs(self.pos.x) > 5000 or abs(self.pos.y) > 5000: self.alive = False
        if abs(self.pos.w) > 3500: self.alive = False

    def get_world_pos(self, world_rot):
        p = self.pos
        for pl in ('XW', 'YW', 'ZW'):
            if abs(world_rot[pl]) > 1e-6:
                p = rot4(p, world_rot[pl], pl)
        return p

    def draw(self, world_rot):
        wp = self.get_world_pos(world_rot)
        # Проекция всех вершин
        screen_v = []
        world_v = []
        for vert in self.verts:
            rv = self.rotate_vertex(vert)
            wx = wp.x + rv[0]; wy = wp.y + rv[1]; wz = wp.z + rv[2]
            world_v.append((wx, wy, wz))
            screen_v.append(proj(wx, wy, wz))

        # Сборка граней
        face_data = []
        for fi, face in enumerate(self.faces):
            pts = []
            valid = True
            z_sum = 0.0
            for idx in face:
                p = screen_v[idx]
                if p is None: valid = False; break
                pts.append((int(p[0]), int(p[1])))
                z_sum += p[3]
            if not valid or len(pts) < 3: continue
            n = len(face)
            z_avg = z_sum / n

            # Нормаль
            i0, i1, i2 = face[0], face[1], face[2]
            a = world_v[i0]; b = world_v[i1]; c = world_v[i2]
            ux = b[0]-a[0]; uy = b[1]-a[1]; uz = b[2]-a[2]
            vx = c[0]-a[0]; vy = c[1]-a[1]; vz = c[2]-a[2]
            nx = uy*vz - uz*vy; ny = uz*vx - ux*vz; nz = ux*vy - uy*vx
            nl = math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0
            nx /= nl; ny /= nl; nz /= nl

            # Освещение
            lx, ly, lz = -0.35, -0.55, -0.75
            dot = nx*lx + ny*ly + nz*lz
            light = 0.42 + 0.58 * abs(dot)
            light *= 0.85 + 0.15 * max(0, -ny)

            base = self.face_colors[fi]

            # Кратер — затемняем
            if fi in self.crater_faces:
                k = self.crater_faces[fi]
                base = (int(base[0]*k), int(base[1]*k), int(base[2]*k))

            # Вспышка от удара
            if self.hit_flash > 0:
                fb = self.hit_flash / 0.3
                base = (min(255, int(base[0] + 220*fb)),
                        min(255, int(base[1] + 100*fb)),
                        min(255, int(base[2] + 100*fb)))

            col = (min(255, int(base[0]*light)),
                   min(255, int(base[1]*light)),
                   min(255, int(base[2]*light)))

            # Металлический блик
            if self.specular > 0:
                d2 = dot * dot
                spec = max(0, d2 * d2 * d2) * self.specular
                col = (min(255, int(col[0] + spec*220)),
                       min(255, int(col[1] + spec*220)),
                       min(255, int(col[2] + spec*230)))

            col = w_color(col, wp.w)
            face_data.append((z_avg, pts, col, wp.w))

        # Сортировка по глубине
        face_data.sort(key=lambda f: -f[0])

        for (_, pts, col, w) in face_data:
            pygame.draw.polygon(screen, col, pts)
            if abs(w) < SLICE_W:
                glow = (min(255, col[0]+70),
                        min(255, col[1]+50),
                        min(255, col[2]+30))
                pygame.draw.polygon(screen, glow, pts, 2)
            else:
                pygame.draw.polygon(screen, (0, 0, 0), pts, 1)

        # Царапины поверх граней
        self._draw_scratches(wp)

        # HP-полоска
        if self.hp < self.max_hp:
            self._draw_hp(wp)

    def _draw_scratches(self, wp):
        """Тонкие тёмные линии на поверхности."""
        # Направление от центра астероида к камере
        cam_dir_x = -wp.x
        cam_dir_y = -wp.y
        cam_dir_z = -wp.z - CAM_Z
        cl = math.sqrt(cam_dir_x**2 + cam_dir_y**2 + cam_dir_z**2) or 1
        cam_dir_x /= cl; cam_dir_y /= cl; cam_dir_z /= cl

        for (p1, p2) in self.scratches:
            rv1 = self.rotate_vertex(p1)
            rv2 = self.rotate_vertex(p2)
            wx1 = wp.x + rv1[0]; wy1 = wp.y + rv1[1]; wz1 = wp.z + rv1[2]
            wx2 = wp.x + rv2[0]; wy2 = wp.y + rv2[1]; wz2 = wp.z + rv2[2]

            # Средняя точка относительно центра
            mx = (wx1 + wx2) * 0.5 - wp.x
            my = (wy1 + wy2) * 0.5 - wp.y
            mz = (wz1 + wz2) * 0.5 - wp.z
            ml = math.sqrt(mx*mx + my*my + mz*mz) or 1
            mx /= ml; my /= ml; mz /= ml

            # Проверка видимости
            if mx * cam_dir_x + my * cam_dir_y + mz * cam_dir_z < 0.25:
                continue

            sp1 = proj(wx1, wy1, wz1)
            sp2 = proj(wx2, wy2, wz2)
            if sp1 is None or sp2 is None: continue

            # Ширина и цвет зависят от расстояния
            dist_k = 600 / max(80, sp1[3])
            lw = max(1, int(1.6 * dist_k))
            shade = max(20, min(90, int(50 * dist_k)))
            col = (shade, shade, shade)

            pygame.draw.line(screen, col,
                             (int(sp1[0]), int(sp1[1])),
                             (int(sp2[0]), int(sp2[1])), lw)

    def _draw_hp(self, wp):
        """Полоска HP над астероидом."""
        p = proj(wp.x, wp.y - self.radius * 1.4, wp.z)
        if p is None: return
        sx, sy, k, rz = p
        if rz > 1800: return
        w = int(50 * k)
        h = max(2, int(5 * k))
        if w < 8: return
        x = int(sx - w/2); y = int(sy - h/2)
        pygame.draw.rect(screen, (60, 20, 20), (x, y, w, h))
        ratio = self.hp / self.max_hp
        col = (220, 200, 60) if ratio > 0.6 else (
              (240, 140, 40) if ratio > 0.3 else (235, 60, 60))
        fill = int(w * ratio)
        pygame.draw.rect(screen, col, (x, y, fill, h))
        pygame.draw.rect(screen, (180, 200, 230), (x, y, w, h), 1)


SHIP_V = [
    (0, 0, 62), (-10, 8, 15), (10, 8, 15), (-10, -6, 15), (10, -6, 15),
    (-10, 8, -25), (10, 8, -25), (-10, -6, -25), (10, -6, -25),
    (-42, 3, -20), (42, 3, -20),
    (-15, 3, 8), (15, 3, 8), (-15, 3, -18), (15, 3, -18),
    (-42, 3, -8), (42, 3, -8),
    (0, 12, 5), (0, 9, -10),
]
SHIP_F = [
    ([0,1,2], (225,240,255)), ([0,2,4], (195,215,240)),
    ([0,4,3], (110,130,165)), ([0,3,1], (155,175,210)),
    ([1,5,18,17], (170,190,220)), ([17,18,6,2], (185,200,230)),
    ([1,3,7,5], (130,150,185)), ([2,6,8,4], (155,175,210)),
    ([3,7,8,4], (75,95,130)), ([5,6,8,7], (55,70,95)),
    ([1,17,2], (40,130,190)), ([17,6,2], (60,150,210)),
    ([1,11,15,9], (175,195,225)), ([11,13,9,15], (145,165,195)),
    ([1,13,11], (110,130,165)), ([5,13,1], (130,150,185)),
    ([2,16,10,12], (180,200,230)), ([12,10,16,14], (150,170,200)),
    ([2,12,14], (115,135,170)), ([6,2,14], (135,155,190)),
]
ENGINES = [(-7, -3, -26), (7, -3, -26), (0, -5, -28)]

class Ship:
    def __init__(self):
        self.x = 0.0; self.y = 0.0
        self.vx = 0.0; self.vy = 0.0
        self.accel = 2200.0
        self.max_sp = 750.0
        self.friction = 2.4
        self.roll = 0.0
        self.lives = 3
        self.invuln = 0.0
        self.engine_pulse = 0.0

    def update(self, keys, dt):
        ax = ay = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  ax -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: ax += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    ay -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  ay += 1
        self.vx += ax * self.accel * dt
        self.vy += ay * self.accel * dt
        if ax == 0: self.vx -= self.vx * self.friction * dt
        if ay == 0: self.vy -= self.vy * self.friction * dt
        sp = math.hypot(self.vx, self.vy)
        if sp > self.max_sp:
            k = self.max_sp / sp; self.vx *= k; self.vy *= k
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -SHIP_LIMIT_X:
            self.x = -SHIP_LIMIT_X; self.vx = abs(self.vx) * 0.4
        if self.x >  SHIP_LIMIT_X:
            self.x =  SHIP_LIMIT_X; self.vx = -abs(self.vx) * 0.4
        if self.y < -SHIP_LIMIT_Y:
            self.y = -SHIP_LIMIT_Y; self.vy = abs(self.vy) * 0.4
        if self.y >  SHIP_LIMIT_Y:
            self.y =  SHIP_LIMIT_Y; self.vy = -abs(self.vy) * 0.4
        tr = -self.vx * 0.002
        self.roll += (tr - self.roll) * 6 * dt
        if self.invuln > 0: self.invuln -= dt
        self.engine_pulse += dt * (12 + abs(sp) / 60)

class FarPlanet:
    def __init__(self):
        self.reset(random.uniform(4000, 9000))
        self.palette = random.choice([
            ((80,130,190),(40,80,140),(150,190,240)),
            ((200,130,90),(120,70,50),(255,180,130)),
            ((180,160,120),(110,95,70),(230,215,175)),
            ((130,100,160),(70,50,100),(190,160,220)),
            ((90,160,130),(50,100,80),(150,220,190)),
            ((200,90,120),(130,50,80),(240,150,180)),
        ])
        self.speed_z = -random.uniform(40, 100)

    def reset(self, z=None):
        self.x = random.uniform(-3500, 3500)
        self.y = random.uniform(-2500, 2500)
        self.z = z if z is not None else random.uniform(4500, 9000)
        self.size = random.uniform(180, 500)

    def update(self, dt):
        self.z += self.speed_z * dt
        if self.z < 300: self.reset()

    def draw(self):
        p = proj(self.x, self.y, self.z)
        if p is None: return
        sx, sy, k, rz = p
        r = int(self.size * k)
        if r < 4 or r > 1500: return
        base, dark, light = self.palette
        depth_alpha = max(60, min(255, int(255 - (self.z/12000)*200)))
        shadow = pygame.Surface((r*2+20, r*2+20), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (*dark, depth_alpha), (r+10, r+10), r)
        screen.blit(shadow, (int(sx)-r-10, int(sy)-r-10))
        for i in range(r, 0, -max(1, r // 20)):
            t = i / r
            col = (int(base[0]*(1-t) + light[0]*t*(1-t*0.3)),
                   int(base[1]*(1-t) + light[1]*t*(1-t*0.3)),
                   int(base[2]*(1-t) + light[2]*t*(1-t*0.3)))
            pygame.draw.circle(screen, col,
                               (int(sx + r*0.15), int(sy + r*0.15)), i)
        halo = get_glow(light, int(r * 1.15))
        if halo:
            halo.set_alpha(50)
            screen.blit(halo, (int(sx)-int(r*1.15), int(sy)-int(r*1.15)))

class Particle:
    def __init__(self, x, y, color=None):
        self.x, self.y = x, y
        a = random.uniform(0, math.tau)
        sp = random.uniform(100, 450)
        self.vx = math.cos(a) * sp
        self.vy = math.sin(a) * sp
        self.life = random.uniform(0.35, 0.8)
        self.max = self.life
        self.color = color or random.choice(
            [ORANGE, YELLOW, RED, WHITE, (255,200,100)])
        self.size = random.uniform(2, 5)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.93; self.vy *= 0.93
        self.life -= dt

    def draw(self, surf):
        k = max(0, self.life / self.max)
        r = max(1, int(self.size * k))
        g = get_glow(self.color, r * 3)
        if g:
            surf.blit(g, (int(self.x)-r*3, int(self.y)-r*3),
                      special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r)

class StarField:
    def __init__(self):
        self.stars = []
        for _ in range(280):
            layer = random.choices([0,1,2], weights=[5,3,1])[0]
            if layer == 0:  size=1; br=random.randint(80,140); sp=random.uniform(200,350)
            elif layer == 1: size=random.randint(1,2); br=random.randint(140,200); sp=random.uniform(350,600)
            else: size=random.randint(2,3); br=random.randint(200,255); sp=random.uniform(600,900)
            self.stars.append({
                'v': V4(random.uniform(-3500,3500), random.uniform(-2500,2500),
                        random.uniform(100,4000), random.uniform(-200,200)),
                'b': br, 'sz': size, 'sp': sp,
                'tw': random.uniform(0,math.tau),
                'tw_s': random.uniform(1.0,2.5),
                'hue': random.choice(['white','blue','warm']),
            })

    def update(self, dt):
        for s in self.stars:
            s['tw'] += s['tw_s'] * dt
            s['v'].z -= s['sp'] * dt
            if s['v'].z < 50:
                s['v'].z = 4000
                s['v'].x = random.uniform(-3500, 3500)
                s['v'].y = random.uniform(-2500, 2500)

    def draw(self, world_rot):
        for s in self.stars:
            v = s['v']
            for pl in ('XW','YW','ZW'):
                if abs(world_rot[pl]) > 1e-6:
                    v = rot4(v, world_rot[pl], pl)
            p = proj(v.x, v.y, v.z)
            if p is None: continue
            sx, sy, k, rz = p
            if sx < -15 or sx > W+15 or sy < -15 or sy > H+15: continue
            tw = 0.7 + 0.3 * math.sin(s['tw'])
            b = max(40, min(255, int(s['b'] * tw)))
            if s['hue'] == 'blue': col = (int(b*0.7), int(b*0.85), b)
            elif s['hue'] == 'warm': col = (b, int(b*0.85), int(b*0.7))
            else: col = (b, b, min(255, b+30))
            col = w_color(col, v.w)
            size = s['sz']
            if size >= 2:
                g = get_glow(col, size*4)
                if g: screen.blit(g, (int(sx)-size*4, int(sy)-size*4),
                                  special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(screen, col, (int(sx), int(sy)), size)
class Button:
    def __init__(self, x, y, w, h, text, color):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text; self.color = color
        self.hover = False
        self.font = pygame.font.Font(None, 30)

    def handle(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos): return True
        return False

    def draw(self, surf):
        col = self.color
        if self.hover: col = tuple(min(255, v+50) for v in col)
        s = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        for y in range(self.rect.h):
            t = y / max(1, self.rect.h-1)
            c = (int(col[0]*(1-t*0.6)), int(col[1]*(1-t*0.6)),
                 int(col[2]*(1-t*0.6)))
            pygame.draw.line(s, c, (0, y), (self.rect.w, y))
        mask = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255,255,255,255),
                         (0,0,self.rect.w,self.rect.h), border_radius=8)
        s.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.rect(s, (200,220,255,200),
                         (0,0,self.rect.w,self.rect.h), 2, border_radius=8)
        surf.blit(s, self.rect.topleft)
        img = self.font.render(self.text, True, WHITE)
        surf.blit(img, img.get_rect(center=self.rect.center))

class Game:
    def __init__(self):
        self.state = "menu"
        self.ship = Ship()
        self.asteroids = []
        self.particles = []
        self.world_rot = {'XW': 0.0, 'YW': 0.0, 'ZW': 0.0}
        self.starfield = StarField()
        self.planets = [FarPlanet() for _ in range(4)]
        self.spawn_t = 0.0
        self.elapsed = 0.0
        self.best = 0.0
        self.dash_cd = 0.0
        self.dash_t = 0.0
        self.dash_v = (0.0, 0.0)
        self.pulse_cd = 0.0
        self.flash = 0.0

        self.f_xs  = pygame.font.Font(None, 20)
        self.f_s   = pygame.font.Font(None, 24)
        self.f_m   = pygame.font.Font(None, 32)
        self.f_l   = pygame.font.Font(None, 48)
        self.f_big = pygame.font.Font(None, 76)

        cx, cy = W//2, H//2
        bw, bh = 280, 52
        self.btn_play   = Button(cx-bw//2, cy-40, bw, bh, "ЗАПУСК", (50,130,90))
        self.btn_quit   = Button(cx-bw//2, cy+40, bw, bh, "ВЫХОД", (140,50,60))
        self.btn_resume = Button(cx-bw//2, cy-80, bw, bh, "ПРОДОЛЖИТЬ", (50,130,90))
        self.btn_menu   = Button(cx-bw//2, cy,    bw, bh, "В МЕНЮ", (60,100,180))
        self.btn_quit2  = Button(cx-bw//2, cy+80, bw, bh, "ВЫХОД", (140,50,60))
        self.btn_retry  = Button(cx-bw//2, cy+60, bw, bh, "ЕЩЁ РАЗ", (50,130,90))
        self.btn_menu2  = Button(cx-bw//2, cy+120,bw, bh, "В МЕНЮ", (60,100,180))

        self.reset()

    def reset(self):
        self.ship = Ship()
        self.asteroids.clear()
        self.particles.clear()
        self.world_rot = {'XW': 0.0, 'YW': 0.0, 'ZW': 0.0}
        self.spawn_t = 0.0
        self.elapsed = 0.0
        self.dash_cd = 0.0
        self.dash_t = 0.0
        self.pulse_cd = 0.0
        self.flash = 0.0
        for _ in range(5):
            self.spawn_asteroid()

    def spawn_asteroid(self):
        self.asteroids.append(Asteroid(
            V4(random.uniform(-500, 500), random.uniform(-400, 400),
               random.uniform(2400, 3400), random.uniform(-180, 180)),
            random.randint(0, 999999)))

    def start_dash(self):
        if self.dash_cd > 0 or self.dash_t > 0: return
        keys = pygame.key.get_pressed()
        dx = dy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if dx == 0 and dy == 0: dy = -1
        n = math.hypot(dx, dy)
        self.dash_v = (dx/n*2400, dy/n*2400)
        self.dash_t = 0.18
        self.dash_cd = 1.2
        self.ship.invuln = max(self.ship.invuln, 0.4)

    def pulse(self):
        if self.pulse_cd > 0: return
        self.pulse_cd = 1.2
        self.flash = 0.35
        for a in self.asteroids:
            wp = a.get_world_pos(self.world_rot)
            if abs(wp.w) < SLICE_W * 1.5:
                d = 1 if wp.w >= 0 else -1
                a.vel.w += d * 500

    def handle(self, ev):
        if ev.type == pygame.QUIT: return "quit"
        if self.state == "menu":
            if self.btn_play.handle(ev):
                self.reset(); self.state = "playing"; return
            if self.btn_quit.handle(ev): return "quit"
        elif self.state == "paused":
            if self.btn_resume.handle(ev): self.state = "playing"; return
            if self.btn_menu.handle(ev):   self.state = "menu";    return
            if self.btn_quit2.handle(ev):  return "quit"
        elif self.state == "game_over":
            if self.btn_retry.handle(ev):
                self.reset(); self.state = "playing"; return
            if self.btn_menu2.handle(ev): self.state = "menu"; return
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                if self.state == "playing": self.state = "paused"
                elif self.state == "paused": self.state = "playing"
                else: return "quit"
            if self.state == "playing":
                if ev.key in (pygame.K_LSHIFT, pygame.K_RSHIFT): self.start_dash()
                if ev.key == pygame.K_SPACE: self.pulse()
            if self.state == "game_over" and ev.key == pygame.K_SPACE:
                self.reset(); self.state = "playing"
        return None

    def update(self, dt):
        if self.flash > 0: self.flash -= dt * 2.5
        if self.pulse_cd > 0: self.pulse_cd -= dt
        self.starfield.update(dt)
        for p in self.planets: p.update(dt)
        if self.state != "playing": return

        keys = pygame.key.get_pressed()
        self.ship.update(keys, dt)
        if self.dash_t > 0:
            self.dash_t -= dt
            self.ship.x += self.dash_v[0] * dt
            self.ship.y += self.dash_v[1] * dt
            self.ship.x = max(-SHIP_LIMIT_X, min(SHIP_LIMIT_X, self.ship.x))
            self.ship.y = max(-SHIP_LIMIT_Y, min(SHIP_LIMIT_Y, self.ship.y))
        if self.dash_cd > 0: self.dash_cd -= dt

        sp = 0.9
        if keys[pygame.K_q]: self.world_rot['XW'] += sp * dt
        if keys[pygame.K_e]: self.world_rot['XW'] -= sp * dt
        if keys[pygame.K_r]: self.world_rot['YW'] += sp * dt
        if keys[pygame.K_f]: self.world_rot['YW'] -= sp * dt
        if keys[pygame.K_t]: self.world_rot['ZW'] += sp * dt
        if keys[pygame.K_g]: self.world_rot['ZW'] -= sp * dt

        self.spawn_t += dt
        interval = max(0.4, 1.0 - self.elapsed * 0.008)
        if self.spawn_t >= interval and len(self.asteroids) < 35:
            self.spawn_t = 0
            self.spawn_asteroid()

        for a in self.asteroids: a.update(dt, self.ship)
        for p in self.particles: p.update(dt)

        # Столкновения — с HP
        if self.ship.invuln <= 0:
            for a in self.asteroids:
                if not a.alive: continue
                wp = a.get_world_pos(self.world_rot)
                if abs(wp.w) < SLICE_W:
                    dx = wp.x - self.ship.x
                    dy = wp.y - self.ship.y
                    if (abs(dx) < a.radius + 15 and
                        abs(dy) < a.radius + 15 and -80 < wp.z < 80):
                        self.ship.lives -= 1
                        self.ship.invuln = 1.5
                        a.hp -= 1
                        a.hit_flash = 0.3
                        if a.hp <= 0:
                            a.alive = False
                        sp_scr = proj(self.ship.x, self.ship.y, 0)
                        if sp_scr:
                            for _ in range(45):
                                self.particles.append(
                                    Particle(sp_scr[0], sp_scr[1]))
                        if self.ship.lives <= 0:
                            self.best = max(self.best, self.elapsed)
                            self.state = "game_over"
                        break

        self.asteroids = [a for a in self.asteroids if a.alive]
        self.particles = [p for p in self.particles if p.life > 0]
        self.elapsed += dt

    def draw_world(self):
        screen.fill(BLACK)
        for p in self.planets: p.draw()
        self.starfield.draw(self.world_rot)
        # Сортировка астероидов по глубине (дальние первыми)
        vis = []
        for a in self.asteroids:
            wp = a.get_world_pos(self.world_rot)
            if wp.z > 50:
                vis.append((wp.z, a))
        vis.sort(key=lambda x: -x[0])
        for (_, a) in vis:
            a.draw(self.world_rot)
        self.draw_ship()
        for p in self.particles: p.draw(screen)

    def draw_ship(self):
        s = self.ship
        cr, sr = math.cos(s.roll), math.sin(s.roll)
        world_v = []
        for (vx, vy, vz) in SHIP_V:
            rx = vx*cr - vy*sr
            ry = vx*sr + vy*cr
            world_v.append((s.x + rx, s.y + ry, vz))
        proj_v = [proj(x, y, z) for (x, y, z) in world_v]
        if s.invuln > 0 and int(s.invuln * 12) % 2 == 0:
            return
        faces = []
        for (indices, base_col) in SHIP_F:
            if any(proj_v[i] is None for i in indices): continue
            z_avg = sum(proj_v[i][2] for i in indices) / len(indices)
            li = 0.55 + 0.45 * max(0.0, 1 - z_avg / 1200)
            col = (int(base_col[0]*li), int(base_col[1]*li), int(base_col[2]*li))
            pts = [(int(proj_v[i][0]), int(proj_v[i][1])) for i in indices]
            faces.append((z_avg, pts, col))
        faces.sort(key=lambda f: -f[0])
        for (_, pts, col) in faces:
            pygame.draw.polygon(screen, col, pts)
            pygame.draw.polygon(screen, (140, 190, 230), pts, 1)

        # Скоростные линии
        sp = math.hypot(s.vx, s.vy)
        if sp > 250:
            scr = proj(s.x, s.y, 0)
            if scr:
                sx, sy, k, rz = scr
                sp_k = min(1.0, (sp - 250) / 500)
                dir_x = -s.vx / sp; dir_y = -s.vy / sp
                perp_x = -dir_y; perp_y = dir_x
                rnd = random.Random(int(self.elapsed * 60))
                for _ in range(6):
                    off = rnd.uniform(-60, 60)
                    length = rnd.uniform(60, 180) * sp_k
                    x1 = sx + perp_x * off + dir_x * 40
                    y1 = sy + perp_y * off + dir_y * 40
                    x2 = x1 + dir_x * length
                    y2 = y1 + dir_y * length
                    alpha = int(120 * sp_k * rnd.uniform(0.4, 1.0))
                    a = max(0, min(255, alpha))
                    ls = pygame.Surface((abs(x2-x1)+4, abs(y2-y1)+4),
                                        pygame.SRCALPHA)
                    pygame.draw.line(ls, (0, 200, 255, a),
                                     (2, 2), (x2-x1+2, y2-y1+2), 1)
                    screen.blit(ls, (min(x1,x2)-2, min(y1,y2)-2))

        # Двигатели
        pulse = 0.7 + 0.3 * math.sin(s.engine_pulse)
        speed_k = max(0.3, sp / s.max_sp)
        for (ex, ey, ez) in ENGINES:
            rl_x = ex*cr - ey*sr
            rl_y = ex*sr + ey*cr
            p = proj(s.x + rl_x, s.y + rl_y, ez)
            if p is None: continue
            sx, sy, k, rz = p
            fr = int(32 * k * pulse * speed_k)
            if fr < 3: continue
            for col, sz, alpha in [(ORANGE, fr, 120),
                                    (YELLOW, int(fr*0.7), 180),
                                    (WHITE, int(fr*0.4), 255)]:
                if sz < 1: continue
                g = get_glow(col, sz)
                if g:
                    g.set_alpha(alpha)
                    screen.blit(g, (int(sx)-sz, int(sy)-sz),
                                special_flags=pygame.BLEND_ADD)

    
    def panel(self, r, alpha=200):
        s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (*PANEL, alpha), (0,0,r.w,r.h), border_radius=10)
        screen.blit(s, r.topleft)
        pygame.draw.rect(screen, BORDER, r, 1, border_radius=10)

    def txt(self, text, font, color, x, y, center=False):
        img = font.render(text, True, color)
        sh  = font.render(text, True, (0,0,0))
        if center:
            screen.blit(sh, sh.get_rect(center=(x+1, y+1)))
            screen.blit(img, img.get_rect(center=(x, y)))
        else:
            screen.blit(sh, sh.get_rect(topleft=(x+1, y+1)))
            screen.blit(img, img.get_rect(topleft=(x, y)))

    def draw_hud(self):
        r = pygame.Rect(15, 15, 200, 82)
        self.panel(r)
        self.txt("ВРЕМЯ", self.f_xs, GREY, 30, 22)
        self.txt(f"{int(self.elapsed)} сек", self.f_m, WHITE, 30, 42)
        self.txt(f"рекорд {int(self.best)}", self.f_xs, CYAN, 30, 78)

        r2 = pygame.Rect(W//2-85, 15, 170, 62)
        self.panel(r2)
        spd = 1.0 + self.elapsed * 0.025
        col = YELLOW if spd < 2 else (ORANGE if spd < 3 else RED)
        self.txt(f"x{spd:.2f}", self.f_m, col, W//2, 32, True)
        self.txt("ТЕМП", self.f_xs, GREY, W//2, 60, True)

        r3 = pygame.Rect(W-180, 15, 165, 62)
        self.panel(r3)
        self.txt("ЖИЗНИ", self.f_xs, GREY, W-165, 22)
        for i in range(3):
            cx = W-145 + i*32; cy = 55
            if i < self.ship.lives:
                g = get_glow(RED, 14)
                if g: screen.blit(g, (cx-14, cy-14),
                                  special_flags=pygame.BLEND_ADD)
                pygame.draw.circle(screen, RED, (cx, cy), 8)
                pygame.draw.circle(screen, (255,220,220), (cx, cy), 8, 2)
            else:
                pygame.draw.circle(screen, (40,40,55), (cx, cy), 8)
                pygame.draw.circle(screen, (80,85,105), (cx, cy), 8, 1)

        sp = math.hypot(self.ship.vx, self.ship.vy)
        r_sp = pygame.Rect(W//2-85, 80, 170, 30)
        self.panel(r_sp)
        sp_k = min(1.0, sp / self.ship.max_sp)
        bar = pygame.Rect(W//2-75, 88, 150, 12)
        pygame.draw.rect(screen, (20,30,50), bar, border_radius=6)
        col_sp = GREEN if sp_k < 0.5 else (YELLOW if sp_k < 0.85 else RED)
        pygame.draw.rect(screen, col_sp,
                         (bar.x, bar.y, int(bar.w*sp_k), bar.h), border_radius=6)
        pygame.draw.rect(screen, BORDER, bar, 1, border_radius=6)
        self.txt(f"{int(sp)}", self.f_xs, WHITE, W//2, 105, True)

        r4 = pygame.Rect(15, H-90, 200, 75)
        self.panel(r4)
        self.txt("РЫВОК [SHIFT]", self.f_xs, GREY, 30, H-84)
        bar = pygame.Rect(30, H-68, 170, 8)
        pygame.draw.rect(screen, (20,30,50), bar, border_radius=4)
        k = 1 - self.dash_cd/1.2 if self.dash_cd > 0 else 1
        k = max(0, min(1, k))
        if k > 0:
            c = GREEN if k >= 1 else (YELLOW if k > 0.4 else RED)
            pygame.draw.rect(screen, c, (bar.x, bar.y, int(bar.w*k), bar.h),
                             border_radius=4)
        pygame.draw.rect(screen, BORDER, bar, 1, border_radius=4)

        self.txt("ИМПУЛЬС [SPACE]", self.f_xs, GREY, 30, H-48)
        bar2 = pygame.Rect(30, H-32, 170, 8)
        pygame.draw.rect(screen, (20,30,50), bar2, border_radius=4)
        k2 = 1 - self.pulse_cd/1.2 if self.pulse_cd > 0 else 1
        k2 = max(0, min(1, k2))
        if k2 > 0:
            c = CYAN if k2 >= 1 else (YELLOW if k2 > 0.4 else RED)
            pygame.draw.rect(screen, c,
                             (bar2.x, bar2.y, int(bar2.w*k2), bar2.h),
                             border_radius=4)
        pygame.draw.rect(screen, BORDER, bar2, 1, border_radius=4)

        r5 = pygame.Rect(W-215, H-105, 200, 90)
        self.panel(r5)
        self.txt("4D ВРАЩЕНИЕ", self.f_xs, GREY, W-200, H-100)
        for i, (key, name, pl) in enumerate([("Q/E","XW",'XW'),
                                              ("R/F","YW",'YW'),
                                              ("T/G","ZW",'ZW')]):
            y = H-78 + i*20
            self.txt(key, self.f_xs, CYAN, W-200, y)
            self.txt(name, self.f_xs, DIM, W-160, y)
            a = self.world_rot[pl]
            v = (math.sin(a) + 1) * 0.5
            bx = W-125; bw = 100
            pygame.draw.rect(screen, (15,25,45), (bx, y+2, bw, 8),
                             border_radius=4)
            pygame.draw.rect(screen, CYAN, (bx, y+2, int(bw*v), 8),
                             border_radius=4)
            pygame.draw.rect(screen, BORDER, (bx, y+2, bw, 8),
                             1, border_radius=4)

        self.txt("WASD · SPACE импульс · SHIFT рывок · "
                 "Q/E R/F T/G 4D · ESC пауза",
                 self.f_xs, GREY, W//2, H-18, True)

    def draw_menu(self):
        screen.fill(BLACK)
        for p in self.planets: p.draw()
        self.starfield.draw(self.world_rot)
        # Демо-камни всех типов
        t = pygame.time.get_ticks() / 1000.0
        for i, (kind, x_off, z_off) in enumerate([
                ('meteorite', -320, 800),
                ('asteroid', 0, 900),
                ('large', 330, 1000)]):
            a = Asteroid(V4(x_off, 0, z_off, 0), i*1234, kind=kind)
            a.rx = t * 0.6 + i
            a.ry = t * 0.4 + i
            a.rz = t * 0.3
            a.draw(self.world_rot)
        ov = pygame.Surface((W,H), pygame.SRCALPHA)
        ov.fill((0,0,15,140)); screen.blit(ov, (0,0))
        self.txt("4D HYPERFLIGHT", self.f_big, CYAN, W//2, 130, True)
        self.txt("метеориты · астероиды · металлы · камень",
                 self.f_s, GREY, W//2, 180, True)
        self.btn_play.draw(screen)
        self.btn_quit.draw(screen)
        if self.best > 0:
            self.txt(f"РЕКОРД  {int(self.best)} сек",
                     self.f_m, YELLOW, W//2, H-50, True)

    def draw_pause(self):
        self.draw_world(); self.draw_hud()
        ov = pygame.Surface((W,H), pygame.SRCALPHA)
        ov.fill((0,0,15,180)); screen.blit(ov, (0,0))
        self.txt("ПАУЗА", self.f_big, YELLOW, W//2, H//2-150, True)
        self.btn_resume.draw(screen); self.btn_menu.draw(screen); self.btn_quit2.draw(screen)

    def draw_game_over(self):
        self.draw_world()
        ov = pygame.Surface((W,H), pygame.SRCALPHA)
        ov.fill((30,0,0,200)); screen.blit(ov, (0,0))
        self.txt("СРЕЗ ПОТЕРЯН", self.f_big, RED, W//2, H//2-160, True)
        r = pygame.Rect(W//2-200, H//2-100, 400, 120)
        self.panel(r, alpha=220)
        self.txt("ВРЕМЯ В 4D", self.f_xs, GREY, W//2, H//2-75, True)
        self.txt(f"{int(self.elapsed)} сек", self.f_l, WHITE, W//2, H//2-35, True)
        if int(self.elapsed) >= int(self.best):
            self.txt("★ НОВЫЙ РЕКОРД ★", self.f_s, YELLOW, W//2, H//2+15, True)
        else:
            self.txt(f"Рекорд: {int(self.best)} сек",
                     self.f_s, CYAN, W//2, H//2+15, True)
        self.btn_retry.draw(screen); self.btn_menu2.draw(screen)

    def draw(self):
        if self.state == "menu":       self.draw_menu()
        elif self.state == "playing":  self.draw_world(); self.draw_hud()
        elif self.state == "paused":   self.draw_pause()
        elif self.state == "game_over": self.draw_game_over()
        if self.flash > 0:
            ov = pygame.Surface((W,H), pygame.SRCALPHA)
            ov.fill((0,220,255, int(70*self.flash)))
            screen.blit(ov, (0,0), special_flags=pygame.BLEND_ADD)


def main():
    g = Game()
    running = True
    dt = 0.0
    while running:
        for ev in pygame.event.get():
            if g.handle(ev) == "quit": running = False
        g.update(dt); g.draw()
        pygame.display.flip()
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
    pygame.quit()
if __name__ == "__main__":
    main()