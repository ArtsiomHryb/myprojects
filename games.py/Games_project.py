# -*- coding: utf-8 -*-
"""
3D Hyperflight — итерация 5: чистые звёзды, правильные тени, космический мусор.
"""
import pygame, math, random
from functools import lru_cache

pygame.init()
W, H = 1000, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("3D Hyperflight")
clock = pygame.time.Clock()
FPS = 60

BLACK = (2, 3, 12); WHITE = (245, 250, 255); CYAN = (0, 220, 240); YELLOW = (255, 220, 80)
ORANGE = (255, 140, 0); RED = (235, 70, 70); GREEN = (100, 230, 140); GREY = (150, 155, 175)
DIM = (80, 90, 110); PANEL = (10, 15, 32); BORDER = (60, 95, 150)

SHIP_LIMIT_X = 550.0
SHIP_LIMIT_Y = 390.0
SHIP_Z = 0.0
CAM_Z = 700.0
FOV_3D = 620.0
NEAR_Z = 60.0
FAR_Z = 6000.0

# ============================================================
#               3D-МАТЕМАТИКА (V3 объявлен ДО SUN_POS)
# ============================================================
class V3:
    __slots__ = ('x', 'y', 'z')
    def __init__(s, x=0.0, y=0.0, z=0.0):
        s.x, s.y, s.z = float(x), float(y), float(z)
    def __add__(s, o): return V3(s.x+o.x, s.y+o.y, s.z+o.z)
    def __sub__(s, o): return V3(s.x-o.x, s.y-o.y, s.z-o.z)
    def __mul__(s, k): return V3(s.x*k, s.y*k, s.z*k)
    __rmul__ = __mul__
    def __repr__(s): return f"V3({s.x:.1f},{s.y:.1f},{s.z:.1f})"

# ---- ГЛОБАЛЬНЫЙ ИСТОЧНИК СВЕТА (СОЛНЦЕ) ----
SUN_POS = V3(3000, -4000, 10000)
SUN_LEN = math.sqrt(SUN_POS.x**2 + SUN_POS.y**2 + SUN_POS.z**2)
LIGHT_DIR = (SUN_POS.x / SUN_LEN, SUN_POS.y / SUN_LEN, SUN_POS.z / SUN_LEN)

def proj(x, y, z):
    rz = z + CAM_Z
    if rz < NEAR_Z: return None
    k = FOV_3D / rz
    return (W/2 + x*k, H/2 + y*k, k, rz)

def perp_to(vx, vy, vz):
    sp = math.sqrt(vx*vx + vy*vy + vz*vz) or 1.0
    if abs(vy) < 0.9 * sp:
        px, py, pz = vz, 0.0, -vx
    else:
        px, py, pz = 0.0, -vz, vy
    pl = math.sqrt(px*px + py*py + pz*pz) or 1.0
    return px/pl, py/pl, pz/pl

@lru_cache(maxsize=1024)
def _glow_surface(cr, cg, cb, radius):
    size = radius * 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    steps = max(4, min(12, radius // 4))
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        a = int(90 * (1 - i / steps) ** 2)
        if a > 0 and r > 0:
            pygame.draw.circle(s, (cr, cg, cb, a), (radius, radius), r)
    return s

def get_glow(color, radius):
    if radius < 1: return None
    return _glow_surface((color[0] // 16) * 16,
                          (color[1] // 16) * 16,
                          (color[2] // 16) * 16,
                          max(4, (radius // 4) * 4))

# ============================================================
#                 ПАЛИТРЫ КАМНЯ
# ============================================================
ROCK_PALETTES = {
    'gray':      {'shades':[(175,175,178),(140,140,143),(110,110,113),(160,160,163)],
                  'specular':0.12, 'vein_colors':[(210,215,220),(190,200,210)]},
    'dark_gray': {'shades':[(105,105,110),(80,80,85),(55,55,60),(95,95,100)],
                  'specular':0.15, 'vein_colors':[(150,155,165),(120,125,135)]},
    'metallic':  {'shades':[(200,205,215),(165,170,180),(105,110,120),(180,185,195)],
                  'specular':0.42,
                  'vein_colors':[(255,220,140),(230,200,120),(210,180,90)]},
    'carbon':    {'shades':[(72,75,82),(52,54,60),(30,32,38),(62,65,72)],
                  'specular':0.08, 'vein_colors':[(140,100,200),(110,70,170)]},
}

def make_rock_mesh(size, seed, n_ring, m_rings, irregularity):
    rnd = random.Random(seed)
    verts = [(0, size*rnd.uniform(0.9, 1.15), 0)]
    rings = []
    for m in range(1, m_rings):
        phi = math.pi * m / m_rings
        y = size * math.cos(phi); r = size * math.sin(phi)
        ring = []
        for n in range(n_ring):
            theta = math.tau * n / n_ring
            rr = r * rnd.uniform(1 - irregularity, 1 + irregularity)
            yy = y * rnd.uniform(1 - irregularity*0.5, 1 + irregularity*0.5)
            if rnd.random() < 0.12: rr *= rnd.uniform(0.55, 0.75)
            elif rnd.random() < 0.08: rr *= rnd.uniform(1.15, 1.35)
            ring.append(len(verts))
            verts.append((rr*math.cos(theta), yy, rr*math.sin(theta)))
        rings.append(ring)
    verts.append((0, -size*rnd.uniform(0.85, 1.15), 0))
    south = len(verts) - 1
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

TRAJ_STRAIGHT = 0
TRAJ_WAVE = 1
TRAJ_SPIRAL = 2
TRAJ_ZIGZAG = 3
TRAJ_ORBITAL = 4

# ============================================================
#                АСТЕРОИД
# ============================================================
class Asteroid:
    KINDS = {
        'meteorite': {'size':(12,22),'n_ring':6,'m_rings':3,'irregularity':0.42,
                      'hp':1,'speed':(320,440),
                      'palettes':['gray','dark_gray','carbon','metallic'],
                      'craters':(3,5),'scratches':(2,4),'veins':(1,2),
                      'spawn_weight':6},
        'asteroid':  {'size':(24,44),'n_ring':8,'m_rings':4,'irregularity':0.33,
                      'hp':2,'speed':(220,320),
                      'palettes':['gray','dark_gray','metallic'],
                      'craters':(6,10),'scratches':(4,7),'veins':(2,4),
                      'spawn_weight':3},
        'large':     {'size':(50,78),'n_ring':10,'m_rings':5,'irregularity':0.24,
                      'hp':3,'speed':(140,200),
                      'palettes':['gray','dark_gray','metallic'],
                      'craters':(10,16),'scratches':(6,10),'veins':(3,6),
                      'spawn_weight':1},
    }

    def __init__(self, pos, seed, kind=None, vel_hint=None, homing=False):
        if kind is None:
            kinds = list(self.KINDS.keys())
            weights = [self.KINDS[k]['spawn_weight'] for k in kinds]
            kind = random.choices(kinds, weights=weights)[0]
        self.kind = kind; cfg = self.KINDS[kind]
        rnd = random.Random(seed); self.seed = seed
        size = rnd.uniform(*cfg['size']); self.scale = size
        self.verts, self.faces = make_rock_mesh(
            size, seed, cfg['n_ring'], cfg['m_rings'], cfg['irregularity'])
        self.hp = cfg['hp']; self.max_hp = cfg['hp']; self.hit_flash = 0.0
        pal = ROCK_PALETTES[rnd.choice(cfg['palettes'])]
        self.specular = pal['specular']
        self.vein_colors = pal['vein_colors']
        self.face_colors = [rnd.choice(pal['shades']) for _ in self.faces]

        self.crater_faces = {}
        for _ in range(rnd.randint(*cfg['craters'])):
            self.crater_faces[rnd.randrange(len(self.faces))] = {
                'depth': rnd.uniform(0.42, 0.68)}

        self.scratches = []
        for _ in range(rnd.randint(*cfg['scratches'])):
            theta = rnd.uniform(0, math.tau); phi = rnd.uniform(0.35, math.pi*0.65)
            r = size * 0.95
            x1 = r*math.sin(phi)*math.cos(theta); y1 = r*math.cos(phi)
            z1 = r*math.sin(phi)*math.sin(theta)
            dth = rnd.uniform(-0.85, 0.85); dph = rnd.uniform(-0.55, 0.55)
            x2 = r*math.sin(phi+dph)*math.cos(theta+dth); y2 = r*math.cos(phi+dph)
            z2 = r*math.sin(phi+dph)*math.sin(theta+dth)
            self.scratches.append(((x1,y1,z1),(x2,y2,z2)))

        self.veins = []
        for _ in range(rnd.randint(*cfg['veins'])):
            theta = rnd.uniform(0, math.tau); phi = rnd.uniform(0.3, math.pi*0.7)
            pts = []
            for k in range(3):
                t = k / 2
                a = theta + t*rnd.uniform(-0.6, 0.6)
                p = phi + t*rnd.uniform(-0.5, 0.5)
                rv = size * 0.92
                pts.append((rv*math.sin(p)*math.cos(a), rv*math.cos(p),
                            rv*math.sin(p)*math.sin(a)))
            self.veins.append({'points':pts, 'color':rnd.choice(self.vein_colors)})

        self.pit_faces = {}
        for _ in range(rnd.randint(3, 8)):
            self.pit_faces[rnd.randrange(len(self.faces))] = rnd.uniform(0.78, 0.92)

        self.trajectory = rnd.choice([TRAJ_STRAIGHT, TRAJ_WAVE, TRAJ_SPIRAL,
                                       TRAJ_ZIGZAG, TRAJ_ORBITAL])
        self.traj_time = rnd.uniform(0, 10)
        self.traj_param = rnd.uniform(0.6, 1.6)

        self.pos = pos
        self.rx = rnd.uniform(0, math.tau); self.ry = rnd.uniform(0, math.tau)
        self.rz = rnd.uniform(0, math.tau)
        self.rvx = rnd.uniform(-0.4, 0.4); self.rvy = rnd.uniform(-0.4, 0.4)
        self.rvz = rnd.uniform(-0.4, 0.4)

        if vel_hint is not None:
            self.vel = vel_hint
        else:
            sp = rnd.uniform(*cfg['speed'])
            self.vel = V3(rnd.uniform(-80, 80), rnd.uniform(-80, 80), -sp)
        self.radius = size * 1.3
        self.alive = True
        self.homing = homing
        self._cx = self._sx = self._cy = self._sy = self._cz = self._sz = 0.0

    def _rotate_velocity_around_forward(self, angle):
        vx, vy, vz = self.vel.x, self.vel.y, self.vel.z
        speed = math.sqrt(vx*vx + vy*vy + vz*vz) or 1.0
        fx, fy, fz = vx/speed, vy/speed, vz/speed
        if abs(fy) < 0.9:
            px, py, pz = fz, 0.0, -fx
            pl = math.sqrt(px*px + pz*pz) or 1.0
            px, pz = px/pl, pz/pl
        else:
            px, py, pz = 1.0, 0.0, 0.0
        qx = fy*pz - fz*py; qy = fz*px - fx*pz; qz = fx*py - fy*px
        vf = vx*fx + vy*fy + vz*fz
        vp = vx*px + vy*py + vz*pz
        vq = vx*qx + vy*qy + vz*qz
        ca, sa = math.cos(angle), math.sin(angle)
        nvp = vp*ca - vq*sa; nvq = vp*sa + vq*ca
        self.vel.x = fx*vf + px*nvp + qx*nvq
        self.vel.y = fy*vf + py*nvp + qy*nvq
        self.vel.z = fz*vf + pz*nvp + qz*nvq

    def update(self, dt, ship):
        self.traj_time += dt
        if self.trajectory == TRAJ_WAVE:
            px, py, pz = perp_to(self.vel.x, self.vel.y, self.vel.z)
            accel = math.sin(self.traj_time * 2.5) * 120 * self.traj_param
            self.vel.x += px * accel * dt
            self.vel.y += py * accel * dt
            self.vel.z += pz * accel * dt
        elif self.trajectory == TRAJ_ZIGZAG:
            px, py, pz = perp_to(self.vel.x, self.vel.y, self.vel.z)
            sign = 1 if int(self.traj_time * 3 * self.traj_param) % 2 == 0 else -1
            accel = sign * 180 * self.traj_param
            self.vel.x += px * accel * dt
            self.vel.y += py * accel * dt
            self.vel.z += pz * accel * dt
        elif self.trajectory == TRAJ_SPIRAL:
            self._rotate_velocity_around_forward(self.traj_param * dt * 1.5)
        elif self.trajectory == TRAJ_ORBITAL:
            ang = self.traj_param * dt * 0.6
            ca, sa = math.cos(ang), math.sin(ang)
            vx = self.vel.x * ca - self.vel.z * sa
            vz = self.vel.x * sa + self.vel.z * ca
            self.vel.x, self.vel.z = vx, vz

        if self.homing:
            dx = ship.x - self.pos.x
            dy = ship.y - self.pos.y
            dz = SHIP_Z - self.pos.z
            d = math.sqrt(dx*dx + dy*dy + dz*dz) or 1.0
            sp = math.sqrt(self.vel.x**2 + self.vel.y**2 + self.vel.z**2) or 300.0
            k = min(1.0, 1.2 * dt)
            self.vel.x += (dx/d*sp - self.vel.x) * k
            self.vel.y += (dy/d*sp - self.vel.y) * k
            self.vel.z += (dz/d*sp - self.vel.z) * k

        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        self.pos.z += self.vel.z * dt
        self.rx += self.rvx * dt; self.ry += self.rvy * dt; self.rz += self.rvz * dt
        if self.hit_flash > 0:
            self.hit_flash = max(0.0, self.hit_flash - dt * 3)

    def is_culled(self):
        if self.pos.z < -400 or self.pos.z > FAR_Z: return True
        if abs(self.pos.x) > 3000 or abs(self.pos.y) > 3000: return True
        p = proj(self.pos.x, self.pos.y, self.pos.z)
        if p is None: return True
        sx, sy = p[0], p[1]
        return abs(sx - W/2) > W*1.5 or abs(sy - H/2) > H*1.5

    def _rotate_vertex(self, v):
        x, y, z = v
        y1 = y*self._cx - z*self._sx; z1 = y*self._sx + z*self._cx
        x2 = x*self._cy + z1*self._sy; z2 = -x*self._sy + z1*self._cy
        return (x2*self._cz - y1*self._sz, x2*self._sz + y1*self._cz, z2)

    def draw(self):
        p = self.pos
        self._cx, self._sx = math.cos(self.rx), math.sin(self.rx)
        self._cy, self._sy = math.cos(self.ry), math.sin(self.ry)
        self._cz, self._sz = math.cos(self.rz), math.sin(self.rz)

        screen_v, world_v = [], []
        for vert in self.verts:
            rv = self._rotate_vertex(vert)
            wx, wy, wz = p.x+rv[0], p.y+rv[1], p.z+rv[2]
            world_v.append((wx, wy, wz))
            screen_v.append(proj(wx, wy, wz))

        p0 = proj(p.x, p.y, p.z)
        screen_r = (self.radius * p0[2]) if p0 else 0
        show_details = screen_r > 12

        face_data = []
        for fi, face in enumerate(self.faces):
            pts = []; z_sum = 0.0; valid = True
            for idx in face:
                sp = screen_v[idx]
                if sp is None: valid = False; break
                pts.append((int(sp[0]), int(sp[1]))); z_sum += sp[3]
            if not valid or len(pts) < 3: continue
            z_avg = z_sum / len(face)
            i0, i1, i2 = face[0], face[1], face[2]
            a = world_v[i0]; b = world_v[i1]; c = world_v[i2]
            ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
            vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
            nx = uy*vz - uz*vy; ny = uz*vx - ux*vz; nz = ux*vy - uy*vx
            nl = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
            nx /= nl; ny /= nl; nz /= nl
            dot = nx*LIGHT_DIR[0] + ny*LIGHT_DIR[1] + nz*LIGHT_DIR[2]
            light = 0.25 + 0.75 * max(0.0, dot)
            base = self.face_colors[fi]
            if fi in self.crater_faces:
                kk = self.crater_faces[fi]['depth']
                base = (int(base[0]*kk), int(base[1]*kk), int(base[2]*kk))
            if fi in self.pit_faces:
                kk = self.pit_faces[fi]
                base = (int(base[0]*kk), int(base[1]*kk), int(base[2]*kk))
            if self.hit_flash > 0:
                fb = self.hit_flash / 0.3
                base = (min(255,int(base[0]+220*fb)), min(255,int(base[1]+100*fb)),
                        min(255,int(base[2]+100*fb)))
            col = (min(255,int(base[0]*light)),
                   min(255,int(base[1]*light)),
                   min(255,int(base[2]*light)))
            r_local = (fi * 2654435761) & 0xFFFFFFFF
            spk = (r_local % 11) - 5
            col = (max(0,min(255,col[0]+spk)),
                   max(0,min(255,col[1]+spk)),
                   max(0,min(255,col[2]+spk)))
            if self.specular > 0:
                d2 = dot*dot
                spec = max(0.0, d2*d2*d2) * self.specular
                col = (min(255,int(col[0]+spec*220)),
                       min(255,int(col[1]+spec*220)),
                       min(255,int(col[2]+spec*230)))
            face_data.append((z_avg, pts, col))

        face_data.sort(key=lambda f: -f[0])
        for (_, pts, col) in face_data:
            pygame.draw.polygon(screen, col, pts)
            pygame.draw.polygon(screen, (0, 0, 0), pts, 1)

        if show_details:
            self._draw_veins(p)
            self._draw_scratches(p)

    def _draw_veins(self, wp):
        cdx, cdy, cdz = -wp.x, -wp.y, -wp.z - CAM_Z
        cl = math.sqrt(cdx*cdx+cdy*cdy+cdz*cdz) or 1.0
        cdx/=cl; cdy/=cl; cdz/=cl
        for vein in self.veins:
            pts = []; visible = True
            for pt in vein['points']:
                rv = self._rotate_vertex(pt)
                wx, wy, wz = wp.x+rv[0], wp.y+rv[1], wp.z+rv[2]
                mx, my, mz = wx-wp.x, wy-wp.y, wz-wp.z
                ml = math.sqrt(mx*mx+my*my+mz*mz) or 1.0
                if (mx/ml)*cdx + (my/ml)*cdy + (mz/ml)*cdz < 0.15:
                    visible = False; break
                sp = proj(wx, wy, wz)
                if sp is None: visible = False; break
                pts.append((int(sp[0]), int(sp[1])))
            if not visible or len(pts) < 2: continue
            col = vein['color']
            pygame.draw.lines(screen, col, False, pts, 2)
            pygame.draw.lines(screen,
                              (min(255,col[0]+40), min(255,col[1]+40), min(255,col[2]+30)),
                              False, pts, 1)

    def _draw_scratches(self, wp):
        cdx, cdy, cdz = -wp.x, -wp.y, -wp.z - CAM_Z
        cl = math.sqrt(cdx*cdx+cdy*cdy+cdz*cdz) or 1.0
        cdx/=cl; cdy/=cl; cdz/=cl
        for (p1, p2) in self.scratches:
            rv1 = self._rotate_vertex(p1); rv2 = self._rotate_vertex(p2)
            wx1, wy1, wz1 = wp.x+rv1[0], wp.y+rv1[1], wp.z+rv1[2]
            wx2, wy2, wz2 = wp.x+rv2[0], wp.y+rv2[1], wp.z+rv2[2]
            mx, my, mz = (wx1+wx2)*0.5-wp.x, (wy1+wy2)*0.5-wp.y, (wz1+wz2)*0.5-wp.z
            ml = math.sqrt(mx*mx+my*my+mz*mz) or 1.0
            if (mx/ml)*cdx + (my/ml)*cdy + (mz/ml)*cdz < 0.25: continue
            sp1 = proj(wx1, wy1, wz1); sp2 = proj(wx2, wy2, wz2)
            if sp1 is None or sp2 is None: continue
            lw = max(1, int(1.6 * 600 / max(80, sp1[3])))
            shade = max(20, min(90, int(50 * 600 / max(80, sp1[3]))))
            pygame.draw.line(screen, (shade, shade, shade),
                             (int(sp1[0]),int(sp1[1])),
                             (int(sp2[0]),int(sp2[1])), lw)

    def draw_hp(self):
        if self.hp >= self.max_hp: return
        p = proj(self.pos.x, self.pos.y - self.radius*1.4, self.pos.z)
        if p is None: return
        sx, sy, k, rz = p
        if rz > 1500: return
        w = int(50*k); h = max(2, int(5*k))
        if w < 10: return
        x = int(sx-w/2); y = int(sy-h/2)
        pygame.draw.rect(screen, (60,20,20), (x,y,w,h))
        ratio = self.hp/self.max_hp
        col = (220,200,60) if ratio>0.6 else ((240,140,40) if ratio>0.3 else (235,60,60))
        pygame.draw.rect(screen, col, (x,y,int(w*ratio),h))
        pygame.draw.rect(screen, (180,200,230), (x,y,w,h), 1)

# ============================================================
#                КОСМИЧЕСКИЙ МУСОР (НОВОЕ)
# ============================================================
class SpaceJunk:
    """Обломки, панели, спутники — быстрые препятствия.
    Появляются после 15 секунд и служат мини-угрозой."""
    KINDS = ('debris', 'panel', 'satellite')

    def __init__(self, pos, seed, vel_hint=None):
        rnd = random.Random(seed)
        self.kind = rnd.choice(self.KINDS)
        self.pos = pos
        self.seed = seed
        self.rx = rnd.uniform(0, math.tau); self.ry = rnd.uniform(0, math.tau)
        self.rz = rnd.uniform(0, math.tau)
        self.rvx = rnd.uniform(-1.8, 1.8)
        self.rvy = rnd.uniform(-1.8, 1.8)
        self.rvz = rnd.uniform(-1.8, 1.8)
        if vel_hint:
            self.vel = vel_hint
        else:
            self.vel = V3(rnd.uniform(-40,40), rnd.uniform(-40,40), -rnd.uniform(400,550))
        self.hp = 1
        self.alive = True
        self.hit_flash = 0.0
        self._cx = self._sx = self._cy = self._sy = self._cz = self._sz = 0.0
        self._build(rnd)

    def _build(self, rnd):
        if self.kind == 'debris':
            size = rnd.uniform(5, 10)
            self.verts, self.faces = make_rock_mesh(size, self.seed, 5, 3, 0.38)
            self.radius = size * 1.2
            base_col = rnd.choice([(95,95,110),(75,75,90),(115,115,130)])
            self.face_colors = [tuple(max(0,min(255, c + rnd.randint(-15,15))) for c in base_col)
                                for _ in self.faces]
            self.specular = 0.35
        elif self.kind == 'panel':
            w = rnd.uniform(9, 15); t = rnd.uniform(1.5, 2.5); d = rnd.uniform(6, 10)
            self.verts = [
                (-w,t,-d),(w,t,-d),(w,t,d),(-w,t,d),
                (-w,-t,-d),(w,-t,-d),(w,-t,d),(-w,-t,d)
            ]
            self.faces = [[0,1,2,3],[4,7,6,5],[0,4,5,1],[1,5,6,2],[2,6,7,3],[3,7,4,0]]
            self.radius = max(w, d) * 1.05
            # Панель: сверху/снизу тёмно-синяя, торцы серые
            self.face_colors = [
                (45,55,95),(45,55,95),(70,72,85),(70,72,85),(70,72,85),(70,72,85)
            ]
            self.specular = 0.55
        elif self.kind == 'satellite':
            bw, bh, bd = 5, 5, 9
            wl = 18  # длина крыла
            self.verts = [
                # тело
                (-bw,bh,-bd),(bw,bh,-bd),(bw,bh,bd),(-bw,bh,bd),
                (-bw,-bh,-bd),(bw,-bh,-bd),(bw,-bh,bd),(-bw,-bh,bd)
            ]
            self.faces = [[0,1,2,3],[4,7,6,5],[0,4,5,1],[1,5,6,2],[2,6,7,3],[3,7,4,0]]
            body_end = 6
            body_c = (195, 160, 95)
            self.face_colors = [body_c] * body_end
            # Левое крыло
            base = len(self.verts)
            self.verts.extend([
                (-bw-wl,-1,-bd+2),(-bw,-1,-bd+2),(-bw,-1,bd-2),(-bw-wl,-1,bd-2),
                (-bw-wl,1,-bd+2),(-bw,1,-bd+2),(-bw,1,bd-2),(-bw-wl,1,bd-2)
            ])
            self.faces.extend([
                [base,base+1,base+2,base+3],
                [base+4,base+7,base+6,base+5],
                [base,base+4,base+5,base+1],
                [base+1,base+5,base+6,base+2],
                [base+2,base+6,base+7,base+3],
                [base+3,base+7,base+4,base]
            ])
            wing_c = (35, 55, 125)
            self.face_colors.extend([wing_c]*6)
            # Правое крыло
            base2 = len(self.verts)
            self.verts.extend([
                (bw,-1,-bd+2),(bw+wl,-1,-bd+2),(bw+wl,-1,bd-2),(bw,-1,bd-2),
                (bw,1,-bd+2),(bw+wl,1,-bd+2),(bw+wl,1,bd-2),(bw,1,bd-2)
            ])
            self.faces.extend([
                [base2,base2+1,base2+2,base2+3],
                [base2+4,base2+7,base2+6,base2+5],
                [base2,base2+4,base2+5,base2+1],
                [base2+1,base2+5,base2+6,base2+2],
                [base2+2,base2+6,base2+7,base2+3],
                [base2+3,base2+7,base2+4,base2]
            ])
            self.face_colors.extend([wing_c]*6)
            self.radius = bw + wl + 4
            self.specular = 0.45

    def update(self, dt):
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        self.pos.z += self.vel.z * dt
        self.rx += self.rvx * dt; self.ry += self.rvy * dt; self.rz += self.rvz * dt
        if self.hit_flash > 0:
            self.hit_flash = max(0.0, self.hit_flash - dt * 3)

    def is_culled(self):
        if self.pos.z < -400 or self.pos.z > FAR_Z: return True
        if abs(self.pos.x) > 3000 or abs(self.pos.y) > 3000: return True
        p = proj(self.pos.x, self.pos.y, self.pos.z)
        if p is None: return True
        sx, sy = p[0], p[1]
        return abs(sx - W/2) > W*1.5 or abs(sy - H/2) > H*1.5

    def _rotate_vertex(self, v):
        x, y, z = v
        y1 = y*self._cx - z*self._sx; z1 = y*self._sx + z*self._cx
        x2 = x*self._cy + z1*self._sy; z2 = -x*self._sy + z1*self._cy
        return (x2*self._cz - y1*self._sz, x2*self._sz + y1*self._cz, z2)

    def draw(self):
        p = self.pos
        self._cx, self._sx = math.cos(self.rx), math.sin(self.rx)
        self._cy, self._sy = math.cos(self.ry), math.sin(self.ry)
        self._cz, self._sz = math.cos(self.rz), math.sin(self.rz)

        screen_v, world_v = [], []
        for vert in self.verts:
            rv = self._rotate_vertex(vert)
            wx, wy, wz = p.x+rv[0], p.y+rv[1], p.z+rv[2]
            world_v.append((wx, wy, wz))
            screen_v.append(proj(wx, wy, wz))

        face_data = []
        for fi, face in enumerate(self.faces):
            pts = []; z_sum = 0.0; valid = True
            for idx in face:
                sp = screen_v[idx]
                if sp is None: valid = False; break
                pts.append((int(sp[0]), int(sp[1]))); z_sum += sp[3]
            if not valid or len(pts) < 3: continue
            z_avg = z_sum / len(face)
            i0, i1, i2 = face[0], face[1], face[2]
            a = world_v[i0]; b = world_v[i1]; c = world_v[i2]
            ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
            vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
            nx = uy*vz - uz*vy; ny = uz*vx - ux*vz; nz = ux*vy - uy*vx
            nl = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
            nx /= nl; ny /= nl; nz /= nl
            dot = nx*LIGHT_DIR[0] + ny*LIGHT_DIR[1] + nz*LIGHT_DIR[2]
            light = 0.3 + 0.7 * max(0.0, dot)
            base = self.face_colors[fi]
            if self.hit_flash > 0:
                fb = self.hit_flash / 0.3
                base = (min(255,int(base[0]+220*fb)), min(255,int(base[1]+100*fb)),
                        min(255,int(base[2]+100*fb)))
            col = (min(255,int(base[0]*light)),
                   min(255,int(base[1]*light)),
                   min(255,int(base[2]*light)))
            if self.specular > 0:
                d2 = dot*dot
                spec = max(0.0, d2*d2*d2) * self.specular
                col = (min(255,int(col[0]+spec*180)),
                       min(255,int(col[1]+spec*180)),
                       min(255,int(col[2]+spec*200)))
            face_data.append((z_avg, pts, col))

        face_data.sort(key=lambda f: -f[0])
        for (_, pts, col) in face_data:
            pygame.draw.polygon(screen, col, pts)
            pygame.draw.polygon(screen, (0, 0, 0), pts, 1)

# ============================================================
#                КОРАБЛЬ
# ============================================================
class Ship:
    SECTIONS = [
        (70,  1.0,  2.0,  2.0), (60,  3.5,  4.5,  4.0),
        (45,  6.5,  7.5,  7.0), (30, 10.0, 10.0,  9.0),
        (10, 12.0, 11.0, 10.0), (-10, 11.0, 10.0,  9.0),
        (-25, 8.0,  8.0,  7.0), (-35, 4.0,  6.0,  5.0),
        (-45, 2.0,  4.0,  3.0),
    ]
    SKELETON = [
        (0, 0, 70, 0, 0, -45),
        (0, 0, 60, -9, 0, 60), (0, 0, 60, 9, 0, 60),
        (0, 0, 45, -14, 0, 45), (0, 0, 45, 14, 0, 45),
        (0, 0, 30, -20, 0, 30), (0, 0, 30, 20, 0, 30),
        (0, 0, 10, -22, 0, 10), (0, 0, 10, 22, 0, 10),
        (0, 0, -10, -20, 0, -10), (0, 0, -10, 20, 0, -10),
        (0, 0, -25, -16, 0, -25), (0, 0, -25, 16, 0, -25),
        (0, 0, -35, -10, 0, -35), (0, 0, -35, 10, 0, -35),
        (-9, 0, 60, -14, 0, 45), (-14, 0, 45, -20, 0, 30),
        (-20, 0, 30, -22, 0, 10), (-22, 0, 10, -20, 0, -10),
        (-20, 0, -10, -16, 0, -25), (-16, 0, -25, -10, 0, -35),
        (9, 0, 60, 14, 0, 45), (14, 0, 45, 20, 0, 30),
        (20, 0, 30, 22, 0, 10), (22, 0, 10, 20, 0, -10),
        (20, 0, -10, 16, 0, -25), (16, 0, -25, 10, 0, -35),
    ]
    MATERIALS = {
        'white':    {'base':(218,224,236),'spec_color':(255,255,255),
                     'spec_strength':0.55,'spec_power':26,'ambient':0.36,
                     'rim_color':(200,230,255),'rim_strength':0.35},
        'white_d':  {'base':(158,168,188),'spec_color':(220,240,255),
                     'spec_strength':0.45,'spec_power':20,'ambient':0.28,
                     'rim_color':(160,200,240),'rim_strength':0.32},
        'bronze':   {'base':(205,140,75),'spec_color':(255,220,150),
                     'spec_strength':0.95,'spec_power':48,'ambient':0.30,
                     'rim_color':(255,200,110),'rim_strength':0.60},
        'bronze_d': {'base':(130,80,40),'spec_color':(255,180,100),
                     'spec_strength':0.80,'spec_power':36,'ambient':0.26,
                     'rim_color':(220,140,70),'rim_strength':0.45},
        'glass':    {'base':(38,90,165),'spec_color':(220,245,255),
                     'spec_strength':1.00,'spec_power':90,'ambient':0.45,
                     'rim_color':(140,200,255),'rim_strength':0.70},
    }
    ENGINES = [(-8, -2, -48), (8, -2, -48), (0, -6, -48)]
    _LIGHT = None
    _HULL_PLATES = None
    _LOCAL_NORMALS = None
    _LOCAL_CENTERS = None

    @classmethod
    def _plate_normal(cls, points, cr, sr, hint):
        if hint == 'up':     nx, ny, nz = 0, 1, 0
        elif hint == 'down': nx, ny, nz = 0, -1, 0
        elif hint == 'left': nx, ny, nz = -1, 0, 0
        elif hint == 'right': nx, ny, nz = 1, 0, 0
        elif hint == 'front': nx, ny, nz = 0, 0, 1
        elif hint == 'back': nx, ny, nz = 0, 0, -1
        else:
            ax, ay, az = points[0]; bx, by, bz = points[1]; cx, cy, cz = points[2]
            ux, uy, uz = bx-ax, by-ay, bz-az
            vx, vy, vz = cx-ax, cy-ay, cz-az
            nx = uy*vz - uz*vy; ny = uz*vx - ux*vz; nz = ux*vy - uy*vx
            nl = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
            nx /= nl; ny /= nl; nz /= nl
            pcx = sum(p[0] for p in points) / len(points)
            pcy = sum(p[1] for p in points) / len(points)
            if nx*pcx + ny*pcy < 0:
                nx, ny, nz = -nx, -ny, -nz
        return (nx*cr - ny*sr, nx*sr + ny*cr, nz)

    @classmethod
    def _lighting(cls, normal, mat_key):
        if cls._LIGHT is None:
            cls._LIGHT = LIGHT_DIR
        LX, LY, LZ = cls._LIGHT
        VX, VY, VZ = 0.0, 0.0, -1.0
        nx, ny, nz = normal
        diff = max(0.0, nx*LX + ny*LY + nz*LZ)
        hx = LX+VX; hy = LY+VY; hz = LZ+VZ
        hl = math.sqrt(hx*hx+hy*hy+hz*hz) or 1.0
        hx/=hl; hy/=hl; hz/=hl
        sdot = max(0.0, nx*hx + ny*hy + nz*hz)
        mat = cls.MATERIALS[mat_key]
        spec = (sdot ** mat['spec_power']) * mat['spec_strength']
        vdot = abs(nx*VX + ny*VY + nz*VZ)
        rim = ((1.0 - vdot) ** 2.5) * mat['rim_strength']
        base = mat['base']; sc = mat['spec_color']; rc = mat['rim_color']
        amb = mat['ambient']
        lit = amb + (1.0 - amb) * diff
        r = base[0]*lit + sc[0]*spec + rc[0]*rim
        g = base[1]*lit + sc[1]*spec + rc[1]*rim
        b = base[2]*lit + sc[2]*spec + rc[2]*rim
        return (min(255,int(r)), min(255,int(g)), min(255,int(b)))

    @classmethod
    def _build_hull(cls):
        if cls._HULL_PLATES is not None:
            return cls._HULL_PLATES
        plates = []
        secs = []
        for (z, hw, ty, by) in cls.SECTIONS:
            secs.append([(-hw, ty, z), (hw, ty, z), (hw, -by, z), (-hw, -by, z)])
        nose = (0, 0, 75); s0 = secs[0]
        plates.append(([nose, s0[0], s0[1]], 'bronze', 'up'))
        plates.append(([nose, s0[1], s0[2]], 'bronze_d', 'right'))
        plates.append(([nose, s0[2], s0[3]], 'bronze_d', 'down'))
        plates.append(([nose, s0[3], s0[0]], 'bronze', 'left'))

        for i in range(len(secs)-1):
            z_mid = (cls.SECTIONS[i][0] + cls.SECTIONS[i+1][0]) * 0.5
            mt, ms = ('bronze','bronze_d') if (z_mid > 40 or z_mid < -20) else ('white','white_d')
            A, B = secs[i], secs[i+1]
            plates.append(([A[0],A[1],B[1],B[0]], mt, 'up'))
            plates.append(([A[1],A[2],B[2],B[1]], ms, 'right'))
            plates.append(([A[3],B[3],B[2],A[2]], ms, 'down'))
            plates.append(([A[0],B[0],B[3],A[3]], ms, 'left'))

        sN = secs[-1]
        plates.append(([sN[0],sN[1],sN[2],sN[3]], 'bronze_d', 'back'))

        plates.append(([(-6.0,9.8,45),(6.0,9.8,45),(8.0,9.8,25),(-8.0,9.8,25)],
                       'glass', 'up'))
        cab_pts = [(-6.0,9.8,45),(6.0,9.8,45),(8.0,9.8,25),(-8.0,9.8,25)]
        cab_bot = [(-6.0,8.0,45),(6.0,8.0,45),(8.0,7.5,25),(-8.0,7.5,25)]
        cab_hints = ['front', 'right', 'back', 'left']
        for k in range(4):
            a = cab_pts[k]; b = cab_pts[(k+1)%4]
            a2 = cab_bot[k]; b2 = cab_bot[(k+1)%4]
            plates.append(([a,b,b2,a2], 'bronze_d', cab_hints[k]))

        for side in (-1, 1):
            x_r = 12.0*side; x_t = 55.0*side
            top = [(x_r,0.8,10),(x_t,0.3,-15),(x_t,0.3,-35),(x_r,0.8,-25)]
            bot = [(x,-0.8,z) for (x,y,z) in top]
            plates.append((top, 'white', 'up'))
            plates.append((list(reversed(bot)), 'white_d', 'down'))
            for k in range(4):
                a = top[k]; b = top[(k+1)%4]
                a2 = bot[k]; b2 = bot[(k+1)%4]
                hint = None
                if k == 0:   hint = 'front'
                elif k == 2: hint = 'back'
                elif k == 1: hint = 'right' if side > 0 else 'left'
                elif k == 3: hint = 'left'  if side > 0 else 'right'
                plates.append(([a,b,b2,a2], 'bronze_d', hint))
            tip = [(x_t,0.3,-15),(x_t,0.3,-35),(x_t,-0.8,-35),(x_t,-0.8,-15)]
            plates.append((tip, 'bronze', 'right' if side > 0 else 'left'))

        cls._HULL_PLATES = plates
        cls._LOCAL_NORMALS = [cls._plate_normal(p[0], 1.0, 0.0, p[2] if len(p) > 2 else None)
                              for p in plates]
        cls._LOCAL_CENTERS = [(sum(v[0] for v in p[0])/len(p[0]),
                                sum(v[1] for v in p[0])/len(p[0]),
                                sum(v[2] for v in p[0])/len(p[0])) for p in plates]
        return plates

    def __init__(self):
        self.x = 0.0; self.y = 0.0
        self.vx = 0.0; self.vy = 0.0
        self.accel = 2200.0; self.max_sp = 750.0; self.friction = 2.4
        self.roll = 0.0; self.lives = 3; self.invuln = 0.0
        self.engine_pulse = 0.0
        Ship._build_hull()

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
        self.x += self.vx * dt; self.y += self.vy * dt
        if self.x < -SHIP_LIMIT_X: self.x = -SHIP_LIMIT_X; self.vx = abs(self.vx)*0.4
        if self.x >  SHIP_LIMIT_X: self.x =  SHIP_LIMIT_X; self.vx = -abs(self.vx)*0.4
        if self.y < -SHIP_LIMIT_Y: self.y = -SHIP_LIMIT_Y; self.vy = abs(self.vy)*0.4
        if self.y >  SHIP_LIMIT_Y: self.y =  SHIP_LIMIT_Y; self.vy = -abs(self.vy)*0.4
        tr = -self.vx * 0.002
        self.roll += (tr - self.roll) * 6 * dt
        if self.invuln > 0: self.invuln -= dt
        self.engine_pulse += dt * (12 + abs(sp)/60)

    def _tx(self, x, y, z, cr, sr):
        rx = x*cr - y*sr; ry = x*sr + y*cr
        return (self.x + rx, self.y + ry, z)

    def draw(self):
        s = self
        cr, sr = math.cos(s.roll), math.sin(s.roll)
        sp = math.hypot(s.vx, s.vy)
        pulse = 0.7 + 0.3 * math.sin(s.engine_pulse)
        speed_k = max(0.3, sp / s.max_sp)

        flashing = (s.invuln > 0 and int(s.invuln * 12) % 2 == 0)
        if flashing: return

        plates = []
        for i, plate in enumerate(Ship._HULL_PLATES):
            points, mat_key = plate[0], plate[1]
            lnx, lny, lnz = Ship._LOCAL_NORMALS[i]
            lcx, lcy, lcz = Ship._LOCAL_CENTERS[i]
            nxr = lnx*cr - lny*sr
            nyr = lnx*sr + lny*cr
            nzr = lnz
            cxr = lcx*cr - lcy*sr
            cyr = lcx*sr + lcy*cr
            wfx, wfy, wfz = self.x + cxr, self.y + cyr, lcz
            tcx, tcy, tcz = -wfx, -wfy, -CAM_Z - wfz
            if nxr*tcx + nyr*tcy + nzr*tcz <= 0:
                continue
            proj_pts = []; valid = True; z_sum = 0.0
            for (px, py, pz) in points:
                wx, wy, wz = s._tx(px, py, pz, cr, sr)
                p = proj(wx, wy, wz)
                if p is None: valid = False; break
                proj_pts.append((int(p[0]), int(p[1]))); z_sum += p[3]
            if not valid or len(proj_pts) < 3: continue
            z_avg = z_sum / len(proj_pts)
            col = Ship._lighting((nxr, nyr, nzr), mat_key)
            plates.append((z_avg, proj_pts, col, mat_key))
        plates.sort(key=lambda f: -f[0])

        for (_, pts, col, mat_key) in plates:
            pygame.draw.polygon(screen, col, pts)
            edge = (int(col[0]*0.5), int(col[1]*0.5), int(col[2]*0.5))
            pygame.draw.polygon(screen, edge, pts, 1)
            if mat_key in ('bronze', 'glass'):
                pygame.draw.polygon(screen,
                    (min(255,col[0]+45), min(255,col[1]+40), min(255,col[2]+30)),
                    pts, 1)

        # Двигатели
        for (ex, ey, ez) in self.ENGINES:
            wx, wy, wz = s._tx(ex, ey, ez, cr, sr)
            p0 = proj(wx, wy, wz)
            if not p0: continue
            flame_len = 60 + 30 * pulse
            tx, ty, tz = s._tx(ex, ey, ez - flame_len, cr, sr)
            p1 = proj(tx, ty, tz)
            if not p1: continue
            sx, sy = p0[0], p0[1]
            ex_sx, ex_sy = p1[0], p1[1]
            dx, dy = ex_sx - sx, ex_sy - sy
            px, py = -dy, dx
            ln = math.hypot(px, py) or 1.0
            px, py = px/ln, py/ln
            width0 = 6 * p0[2] * speed_k
            width1 = 12 * p0[2] * speed_k * pulse
            poly = [
                (int(sx + px*width0), int(sy + py*width0)),
                (int(ex_sx + px*width1), int(ex_sy + py*width1)),
                (int(ex_sx - px*width1), int(ex_sy - py*width1)),
                (int(sx - px*width0), int(sy - py*width0))
            ]
            pygame.draw.polygon(screen, (255, 100, 0), poly)
            poly_in = [
                (int(sx + px*width0*0.5), int(sy + py*width0*0.5)),
                (int(ex_sx + px*width1*0.4), int(ex_sy + py*width1*0.4)),
                (int(ex_sx - px*width1*0.4), int(ex_sy - py*width1*0.4)),
                (int(sx - px*width0*0.5), int(sy - py*width0*0.5))
            ]
            pygame.draw.polygon(screen, (255, 240, 180), poly_in)
            g = get_glow((255, 160, 50), int(10 * p0[2] * speed_k))
            if g:
                tmp = g.copy(); tmp.set_alpha(180)
                screen.blit(tmp, (int(sx)-g.get_width()//2, int(sy)-g.get_height()//2),
                            special_flags=pygame.BLEND_ADD)

        for (x1,y1,z1,x2,y2,z2) in self.SKELETON:
            wx1, wy1, wz1 = s._tx(x1,y1,z1, cr, sr)
            wx2, wy2, wz2 = s._tx(x2,y2,z2, cr, sr)
            p1 = proj(wx1,wy1,wz1); p2 = proj(wx2,wy2,wz2)
            if p1 is None or p2 is None: continue
            lw = max(1, min(3, int(2.4 * (p1[2]+p2[2]) / 2)))
            pygame.draw.line(screen, (35,42,58),
                             (int(p1[0]),int(p1[1])),
                             (int(p2[0]),int(p2[1])), lw)

        rivets = [(-6,9.3,24),(6,9.3,24),(-6,9.3,8),(6,9.3,8),
                  (-6,9.3,-8),(6,9.3,-8),(-5,9.3,-22),(5,9.3,-22),
                  (-22,1.3,-14),(-30,1.3,-18),(22,1.3,-14),(30,1.3,-18)]
        for (rx, ry, rz) in rivets:
            wx, wy, wz = s._tx(rx, ry, rz, cr, sr)
            p = proj(wx, wy, wz)
            if p is None: continue
            d = max(1, min(3, int(p[2] * 0.9)))
            pygame.draw.circle(screen, (30,25,20),
                               (int(p[0]+d*0.4), int(p[1]+d*0.4)), d)
            pygame.draw.circle(screen, (140,118,88), (int(p[0]), int(p[1])), d)
            if d >= 2:
                pygame.draw.circle(screen, (225,205,170),
                                   (int(p[0]-d*0.4), int(p[1]-d*0.4)), max(1, d-2))

# ============================================================
#                 ПЛАНЕТЫ
# ============================================================
class SolarPlanet:
    DATA = {
        'mercury': {'colors':((150,145,135),(100,95,90),(200,195,185)),
                    'spot':(80,75,70),'type':'rocky','size':(180,260)},
        'venus':   {'colors':((220,190,120),(160,120,50),(255,235,180)),
                    'spot':(255,210,150),'type':'cloudy','size':(220,320)},
        'earth':   {'colors':((50,100,180),(20,50,120),(100,160,220)),
                    'spot':(60,120,60),'type':'earth','size':(220,320)},
        'mars':    {'colors':((190,90,50),(120,50,30),(230,140,90)),
                    'spot':(70,35,25),'type':'mars','size':(180,260)},
        'jupiter': {'colors':((200,170,130),(140,100,60),(235,200,160)),
                    'spot':(180,80,60),'type':'gas','size':(420,620)},
        'saturn':  {'colors':((220,200,150),(160,140,100),(240,230,200)),
                    'spot':(190,170,120),'type':'ring','size':(380,540)},
        'uranus':  {'colors':((140,210,220),(90,150,170),(200,240,250)),
                    'spot':(120,180,200),'type':'gas','size':(220,320)},
        'neptune': {'colors':((60,100,190),(30,60,130),(100,150,220)),
                    'spot':(40,70,140),'type':'gas','size':(220,320)},
    }
    ORDER = ['mercury','venus','earth','mars','jupiter','saturn','uranus','neptune']

    def __init__(self, kind):
        self.kind = kind
        self.colors = self.DATA[kind]['colors']
        self.spot_color = self.DATA[kind]['spot']
        self.planet_type = self.DATA[kind]['type']
        self._mask = None; self._mask_r = -1
        self._term = None; self._term_r = -1
        self._atmo = None; self._atmo_r = -1
        self._respawn()

    def _respawn(self):
        d = self.DATA[self.kind]
        self.x = random.uniform(-3000, 3000)
        self.y = random.uniform(-2000, 2000)
        self.z = random.uniform(5500, 9000)
        self.size = random.uniform(*d['size'])
        self.speed_z = -random.uniform(30, 70)
        self.rotation = random.uniform(0, math.tau)
        self.rot_speed = random.uniform(-0.1, 0.1)
        self.spots = self._generate_spots()
        self.bands = self._generate_bands()
        self.clouds = self._generate_clouds()
        self.storms = self._generate_storms()
        self.cloud_offset = 0.0
        self.storm_phase = 0.0

    def _generate_spots(self):
        rnd = random.Random(hash(self.kind) + 1)
        n = {'rocky':20,'cloudy':0,'earth':15,'mars':18,'gas':0,'ring':0}.get(
            self.planet_type, 0)
        return [(rnd.uniform(0,math.tau), rnd.uniform(-1.2,1.2),
                 rnd.uniform(0.08,0.25), rnd.uniform(0.6,1.0)) for _ in range(n)]

    def _generate_bands(self):
        rnd = random.Random(hash(self.kind) + 42)
        return [( (i+0.5)/20, rnd.uniform(0.8,1.2)/20,
                  rnd.choice([0,0,1,2]), rnd.uniform(0.8,1.0)) for i in range(20)]

    def _generate_clouds(self):
        if self.planet_type not in ('cloudy','earth'): return []
        rnd = random.Random(hash(self.kind) + 777)
        n = 18 if self.planet_type == 'cloudy' else 12
        return [(rnd.uniform(0,math.tau), rnd.uniform(-1.0,1.0),
                 rnd.uniform(0.12,0.30)) for _ in range(n)]

    def _generate_storms(self):
        if self.planet_type not in ('gas','ring'): return []
        rnd = random.Random(hash(self.kind) + 999)
        n = 6 if self.kind == 'jupiter' else 4
        return [{'lon': rnd.uniform(0,math.tau),
                 'lat': rnd.uniform(-0.8,0.8),
                 'size': rnd.uniform(0.08,0.18),
                 'color': rnd.choice([(240,240,240),(230,200,160),
                                       (200,100,80),(180,90,60)]),
                 'phase': rnd.uniform(0,math.tau)} for _ in range(n)]

    def update(self, dt):
        self.z += self.speed_z * dt
        self.rotation += self.rot_speed * dt
        self.cloud_offset += 0.03 * dt
        self.storm_phase += 0.4 * dt
        if self.z < 300: self._respawn()

    def _sphere_xy(self, lon, lat, r, cx, cy):
        x3 = math.cos(lat) * math.sin(lon + self.rotation)
        y3 = math.sin(lat)
        z3 = math.cos(lat) * math.cos(lon + self.rotation)
        if z3 <= 0: return None
        return (cx + x3*r, cy - y3*r, z3)

    def _get_mask(self, r):
        if self._mask_r == r: return self._mask
        size = r*2 + 4
        self._mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self._mask, (255,255,255,255), (r+2, r+2), r)
        self._mask_r = r
        return self._mask

    def _get_term(self, r):
        """Терминатор — тень на стороне, противоположной Солнцу."""
        if self._term_r == r: return self._term
        size = r*2 + 4
        self._term = pygame.Surface((size, size), pygame.SRCALPHA)
        pcx = pcy = r + 2
        # Направление тени = ПРОТИВ направления на Солнце (в экранных координатах)
        shadow_dx = -LIGHT_DIR[0]
        shadow_dy = -LIGHT_DIR[1]
        steps = 18
        for i in range(steps):
            t = (i + 1) / steps
            # Центр сдвигается к тёмной стороне
            cx_ = pcx + int(r * shadow_dx * t * 0.75)
            cy_ = pcy + int(r * shadow_dy * t * 0.75)
            rad = int(r * (1.0 + t * 0.05))
            alpha = int(140 * t)
            if alpha > 0 and rad > 0:
                pygame.draw.circle(self._term, (0,0,0,alpha), (cx_, cy_), rad)
        # Обрезаем по диску планеты
        self._term.blit(self._get_mask(r), (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        self._term_r = r
        return self._term

    def _get_atmo(self, r):
        if self._atmo_r == r: return self._atmo
        base, dark, light = self.colors
        size = r*2 + 40; acx = acy = r + 20
        self._atmo = pygame.Surface((size, size), pygame.SRCALPHA)
        # Свечение на солнечной стороне (рассеяние)
        sun_dx = LIGHT_DIR[0] * 2
        sun_dy = LIGHT_DIR[1] * 2
        for i in range(6, 0, -1):
            rr = r + i * 2
            off_x = int(i * sun_dx)
            off_y = int(i * sun_dy)
            alpha = int(22 * (1 - i/6))  # ослаблено с 45 до 22
            if alpha > 0 and rr > 0:
                pygame.draw.circle(self._atmo, (*light, alpha),
                                   (acx+off_x, acy+off_y), rr)
        inner = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(inner, (255,255,255,255), (acx, acy), r)
        self._atmo.blit(inner, (0,0), special_flags=pygame.BLEND_RGBA_SUB)
        self._atmo_r = r
        return self._atmo

    def draw(self):
        p = proj(self.x, self.y, self.z)
        if p is None: return
        sx, sy, k, rz = p
        r = int(self.size * k)
        if r < 6 or r > 600: return
        base, dark, light = self.colors
        cx, cy = int(sx), int(sy)

        if self.planet_type == 'ring':
            self._draw_ring(cx, cy, r, half='back')

        planet_surf = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
        pcx = pcy = r + 2
        pygame.draw.circle(planet_surf, base, (pcx, pcy), r)
        if r >= 20:
            self._draw_surface(planet_surf, pcx, pcy, r)
        planet_surf.blit(self._get_mask(r), (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(planet_surf, (cx - pcx, cy - pcy))

        screen.blit(self._get_term(r), (cx - pcx, cy - pcy))
        screen.blit(self._get_atmo(r), (cx - (r+20), cy - (r+20)))

        if self.planet_type == 'ring':
            self._draw_ring(cx, cy, r, half='front')

    def _draw_surface(self, surf, cx, cy, r):
        base, dark, light = self.colors

        if self.planet_type in ('rocky', 'mars'):
            for (lon, lat, size, tone) in self.spots:
                res = self._sphere_xy(lon, lat, r, cx, cy)
                if res is None: continue
                px, py, z3 = res
                if z3 < 0.05: continue
                cr = max(2, int(size * r * z3))
                pygame.draw.circle(surf, dark, (int(px+cr*0.3), int(py+cr*0.3)), cr)
                pygame.draw.circle(surf, base, (int(px), int(py)), max(1, int(cr*0.8)))
                pygame.draw.circle(surf, light, (int(px-cr*0.2), int(py-cr*0.2)), max(1, int(cr*0.4)))
            if self.kind == 'mars':
                pygame.draw.ellipse(surf, (240,245,255), (cx-r*0.5, cy-r-1, r*1.0, r*0.15))
                pygame.draw.ellipse(surf, (240,245,255), (cx-r*0.5, cy+r-r*0.15, r*1.0, r*0.15))

        elif self.planet_type == 'earth':
            for (lon, lat, size, tone) in self.spots:
                res = self._sphere_xy(lon, lat, r, cx, cy)
                if res is None: continue
                px, py, z3 = res
                if z3 < 0.05: continue
                cr = max(2, int(size * r * z3))
                col = self.spot_color
                lk = 0.4 + 0.6 * z3
                cc = (int(col[0]*lk), int(col[1]*lk), int(col[2]*lk))
                pygame.draw.circle(surf, cc, (int(px), int(py)), cr)
                pygame.draw.circle(surf, cc, (int(px+cr*0.5), int(py+cr*0.2)), max(1, int(cr*0.7)))
                pygame.draw.circle(surf, cc, (int(px-cr*0.4), int(py+cr*0.4)), max(1, int(cr*0.6)))
                pygame.draw.circle(surf, cc, (int(px+cr*0.1), int(py-cr*0.5)), max(1, int(cr*0.5)))
            pygame.draw.ellipse(surf, (235,245,255), (cx-r*0.55, cy-r-1, r*1.1, r*0.18))
            pygame.draw.ellipse(surf, (235,245,255), (cx-r*0.55, cy+r-r*0.18, r*1.1, r*0.18))
            for (lon, lat, size) in self.clouds:
                res = self._sphere_xy(lon+self.cloud_offset, lat, r, cx, cy)
                if res is None: continue
                px, py, z3 = res
                if z3 < 0.1: continue
                cr = max(2, int(size*r*z3))
                cloud = pygame.Surface((cr*4, cr*2), pygame.SRCALPHA)
                pygame.draw.ellipse(cloud, (255,255,255,120), (0,0,cr*4,cr*2))
                pygame.draw.ellipse(cloud, (255,255,255,180), (cr,cr//2,cr*2,cr))
                surf.blit(cloud, (int(px-cr*2), int(py-cr)))

        elif self.planet_type == 'cloudy':
            for (lon, lat, size) in self.clouds:
                res = self._sphere_xy(lon+self.cloud_offset*0.5, lat, r, cx, cy)
                if res is None: continue
                px, py, z3 = res
                if z3 < 0.05: continue
                cr = max(3, int(size*r*z3*1.5))
                cloud = pygame.Surface((cr*4, cr*3), pygame.SRCALPHA)
                pygame.draw.ellipse(cloud, (*light,80), (0,0,cr*4,cr*2))
                pygame.draw.ellipse(cloud, (255,250,220,120), (cr//2,cr//2,cr*3,cr*1.5))
                surf.blit(cloud, (int(px-cr*2), int(py-cr*1.5)))

        elif self.planet_type in ('gas', 'ring'):
            for (t, width, tone, bright) in self.bands:
                y_off = (t - 0.5) * 2 * r
                band_h = width * 2 * r
                half_w = math.sqrt(max(0, r*r - y_off*y_off))
                if half_w < 2: continue
                if tone == 0:   col = base
                elif tone == 1: col = dark
                else:           col = light
                col = (int(col[0]*bright), int(col[1]*bright), int(col[2]*bright))
                pygame.draw.rect(surf, col, (cx-half_w, cy+y_off-band_h/2, half_w*2, band_h))
            for storm in self.storms:
                res = self._sphere_xy(storm['lon']+self.cloud_offset*0.3, storm['lat'], r, cx, cy)
                if res is None: continue
                px, py, z3 = res
                if z3 < 0.1: continue
                cr = max(3, int(storm['size']*r*z3))
                pygame.draw.ellipse(surf, tuple(min(255,c+40) for c in storm['color']),
                    (int(px-cr*1.6), int(py-cr*0.7), int(cr*3.2), int(cr*1.4)))
                pygame.draw.ellipse(surf, storm['color'],
                    (int(px-cr*1.2), int(py-cr*0.55), int(cr*2.4), int(cr*1.1)))

    def _draw_ring(self, cx, cy, r, half):
        rc1, rc2, rc3, rc4 = ((230,210,160),(200,175,120),(170,145,95),(240,220,180))
        start, end = (0, math.pi) if half == 'back' else (math.pi, math.tau)
        rects = [
            (pygame.Rect(cx-int(r*2.4), cy-int(r*0.44), int(r*4.8), int(r*0.88)), rc3, max(2, r//18)),
            (pygame.Rect(cx-int(r*2.15), cy-int(r*0.40), int(r*4.3), int(r*0.80)), rc2, max(2, r//20)),
            (pygame.Rect(cx-int(r*1.9), cy-int(r*0.35), int(r*3.8), int(r*0.70)), rc1, max(1, r//22)),
            (pygame.Rect(cx-int(r*1.7), cy-int(r*0.30), int(r*3.4), int(r*0.60)), rc4, max(1, r//26)),
        ]
        for rect, col, width in rects:
            pygame.draw.arc(screen, col, rect, start, end, width)

# ============================================================
#                ЧАСТИЦЫ / ЗВЁЗДЫ
# ============================================================
class Particle:
    def __init__(self, x, y, color=None):
        self.x, self.y = x, y
        a = random.uniform(0, math.tau); sp = random.uniform(100, 450)
        self.vx = math.cos(a)*sp; self.vy = math.sin(a)*sp
        self.life = random.uniform(0.35, 0.8); self.max = self.life
        self.color = color or random.choice([ORANGE,YELLOW,RED,WHITE,(255,200,100)])
        self.size = random.uniform(2, 5)
    def update(self, dt):
        self.x += self.vx*dt; self.y += self.vy*dt
        self.vx *= 0.93; self.vy *= 0.93; self.life -= dt
    def draw(self, surf):
        kk = max(0, self.life/self.max); r = max(1, int(self.size*kk))
        g = get_glow(self.color, r*3)
        if g:
            surf.blit(g, (int(self.x)-r*3, int(self.y)-r*3), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r)


class StarField:
    """Звёзды: 1px точки, без «кругов» на экране."""
    def __init__(self):
        # Статичный глубокий фон
        self.bg_stars = []
        for _ in range(400):
            x = random.randint(0, W-1)
            y = random.randint(0, H-1)
            c = random.choice([(180,180,220),(210,210,240),(200,200,255),(170,170,200),(220,220,230)])
            self.bg_stars.append((x, y, c))
        # Динамические звёзды — 1px точки
        self.stars = []
        for _ in range(160):
            layer = random.choices([0,1,2], weights=[5,3,1])[0]
            if layer == 0:
                br = random.randint(60,100); sp = random.uniform(150,300)
            elif layer == 1:
                br = random.randint(100,160); sp = random.uniform(300,500)
            else:
                br = random.randint(160,220); sp = random.uniform(500,800)
            self.stars.append({
                'x': random.uniform(-3000,3000),
                'y': random.uniform(-2000,2000),
                'z': random.uniform(100,4000),
                'b': br, 'sp': sp,
                'tw': random.uniform(0, math.tau),
                'tw_s': random.uniform(1.0, 2.5),
                'hue': random.choice(['white','blue','warm'])
            })

    def update(self, dt):
        for s in self.stars:
            s['tw'] += s['tw_s']*dt
            s['z'] -= s['sp']*dt
            if s['z'] < 50:
                s['z'] = 4000
                s['x'] = random.uniform(-3000,3000)
                s['y'] = random.uniform(-2000,2000)

    def draw_background(self):
        # Фоновые звёзды (1px)
        for (x, y, c) in self.bg_stars:
            screen.set_at((x, y), c)
        # Солнце (яркая точка + мягкое гало)
        p_sun = proj(SUN_POS.x, SUN_POS.y, SUN_POS.z)
        if p_sun:
            sx, sy, k, rz = p_sun
            g = get_glow((255, 250, 220), 120)
            if g:
                tmp = g.copy(); tmp.set_alpha(180)
                screen.blit(tmp, (int(sx)-120, int(sy)-120),
                            special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(screen, (255,255,240), (int(sx), int(sy)), 12)

    def draw_foreground(self):
        """Динамические звёзды-точки. Никаких кругов."""
        for s in self.stars:
            p = proj(s['x'], s['y'], s['z'])
            if p is None: continue
            sx, sy, k, rz = p
            ix, iy = int(sx), int(sy)
            if ix < 0 or ix >= W or iy < 0 or iy >= H: continue
            tw = 0.7 + 0.3*math.sin(s['tw'])
            b = max(30, min(220, int(s['b']*tw)))
            if s['hue'] == 'blue': col = (int(b*0.7),int(b*0.85),b)
            elif s['hue'] == 'warm': col = (b,int(b*0.85),int(b*0.7))
            else: col = (b, b, min(255, b+20))

            # Близкие звёзды — короткий штрих по направлению движения
            if rz < 260:
                dx = sx - W/2
                dy = sy - H/2
                dl = math.hypot(dx, dy) or 1.0
                dx /= dl; dy /= dl
                length = max(2, min(18, int(50 * k * (s['sp'] / 800))))
                ex = int(sx + dx * length)
                ey = int(sy + dy * length)
                pygame.draw.line(screen, col, (ix, iy), (ex, ey), 1)
            else:
                # Дальние — одиночный пиксель
                screen.set_at((ix, iy), col)

# ============================================================
#                КНОПКА
# ============================================================
_BTN_FONT = None
def _get_btn_font():
    global _BTN_FONT
    if _BTN_FONT is None:
        _BTN_FONT = pygame.font.Font(None, 30)
    return _BTN_FONT

class Button:
    def __init__(self, x, y, w, h, text, color):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text; self.color = color
        self.hover = False
    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos): return True
        return False
    def draw(self, surf):
        self.hover = self.rect.collidepoint(pygame.mouse.get_pos())
        col = self.color
        if self.hover: col = tuple(min(255, v+50) for v in col)
        s = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        for y in range(self.rect.h):
            t = y / max(1, self.rect.h-1)
            c = (int(col[0]*(1-t*0.6)), int(col[1]*(1-t*0.6)), int(col[2]*(1-t*0.6)))
            pygame.draw.line(s, c, (0,y), (self.rect.w,y))
        mask = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255,255,255,255), (0,0,self.rect.w,self.rect.h),
                         border_radius=8)
        s.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.rect(s, (200,220,255,200), (0,0,self.rect.w,self.rect.h), 2,
                         border_radius=8)
        surf.blit(s, self.rect.topleft)
        img = _get_btn_font().render(self.text, True, WHITE)
        surf.blit(img, img.get_rect(center=self.rect.center))

# ============================================================
#                ИГРА
# ============================================================
class Game:
    def __init__(self):
        self.state = "menu"; self.ship = Ship()
        self.asteroids = []; self.particles = []
        self.junk = []
        self.starfield = StarField()
        self.planets = [SolarPlanet(k) for k in
                        random.choices(SolarPlanet.ORDER, k=5)]
        self.spawn_t = 0.0; self.elapsed = 0.0; self.best = 0.0
        self.dash_cd = 0.0; self.dash_t = 0.0; self.dash_v = (0.0, 0.0)
        self.pulse_cd = 0.0; self.flash = 0.0
        self.junk_timer = 0.0
        self.junk_start_at = 15.0
        self.last_input_dir = (0.0, -1.0)
        self.f_xs = pygame.font.Font(None, 20); self.f_s = pygame.font.Font(None, 24)
        self.f_m = pygame.font.Font(None, 32); self.f_l = pygame.font.Font(None, 48)
        self.f_big = pygame.font.Font(None, 76)
        cx, cy = W//2, H//2; bw, bh = 280, 52
        self.btn_play = Button(cx-bw//2, cy-40, bw, bh, "ЗАПУСК", (50,130,90))
        self.btn_quit = Button(cx-bw//2, cy+40, bw, bh, "ВЫХОД", (140,50,60))
        self.btn_resume = Button(cx-bw//2, cy-80, bw, bh, "ПРОДОЛЖИТЬ", (50,130,90))
        self.btn_menu = Button(cx-bw//2, cy, bw, bh, "В МЕНЮ", (60,100,180))
        self.btn_quit2 = Button(cx-bw//2, cy+80, bw, bh, "ВЫХОД", (140,50,60))
        self.btn_retry = Button(cx-bw//2, cy+60, bw, bh, "ЕЩЁ РАЗ", (50,130,90))
        self.btn_menu2 = Button(cx-bw//2, cy+120, bw, bh, "В МЕНЮ", (60,100,180))
        self.reset()

    def reset(self):
        self.ship = Ship(); self.asteroids.clear(); self.particles.clear()
        self.junk.clear()
        self.spawn_t = 0.0; self.elapsed = 0.0
        self.dash_cd = 0.0; self.dash_t = 0.0; self.pulse_cd = 0.0; self.flash = 0.0
        self.junk_timer = 0.0
        for _ in range(5): self.spawn_asteroid()

    def _spawn_from_cone(self, speed_range):
        ah = random.uniform(-0.6, 0.6)
        av = random.uniform(-0.4, 0.4)
        dist = random.uniform(2200, 3200)
        x = math.sin(ah) * dist
        y = math.sin(av) * dist * 0.7
        z = math.cos(max(abs(ah), abs(av))) * dist
        tx = self.ship.x + random.uniform(-200, 200)
        ty = self.ship.y + random.uniform(-200, 200)
        dx, dy, dz = tx-x, ty-y, -z
        d = math.sqrt(dx*dx+dy*dy+dz*dz) or 1.0
        speed = random.uniform(*speed_range)
        v = V3(dx/d*speed, dy/d*speed, dz/d*speed)
        return V3(x,y,z), v

    def spawn_asteroid(self):
        pos, v = self._spawn_from_cone((280, 420))
        homing = random.random() < 0.15
        self.asteroids.append(Asteroid(pos, random.randint(0, 999999),
                                        vel_hint=v, homing=homing))

    def spawn_junk(self):
        pos, v = self._spawn_from_cone((380, 540))
        self.junk.append(SpaceJunk(pos, random.randint(0, 999999), vel_hint=v))

    def start_dash(self):
        if self.dash_cd > 0 or self.dash_t > 0: return
        dx, dy = self.last_input_dir
        n = math.hypot(dx, dy) or 1.0
        self.dash_v = (dx/n*2400, dy/n*2400)
        self.dash_t = 0.18
        self.dash_cd = 1.2
        self.ship.invuln = max(self.ship.invuln, 0.4)

    def pulse(self):
        if self.pulse_cd > 0: return
        self.pulse_cd = 1.2; self.flash = 0.35
        R = 500.0
        for a in self.asteroids + self.junk:
            dx = a.pos.x - self.ship.x
            dy = a.pos.y - self.ship.y
            dz = a.pos.z - SHIP_Z
            d = math.sqrt(dx*dx+dy*dy+dz*dz)
            if 1 < d < R:
                push = (1 - d/R) * 600
                a.vel.x += dx/d * push
                a.vel.y += dy/d * push
                a.vel.z += dz/d * push

    def handle(self, ev):
        if ev.type == pygame.QUIT: return "quit"
        if ev.type == pygame.WINDOWFOCUSLOST and self.state == "playing":
            self.state = "paused"; return
        if self.state == "menu":
            if self.btn_play.handle(ev): self.reset(); self.state="playing"; return
            if self.btn_quit.handle(ev): return "quit"
        elif self.state == "paused":
            if self.btn_resume.handle(ev): self.state="playing"; return
            if self.btn_menu.handle(ev): self.state="menu"; return
            if self.btn_quit2.handle(ev): return "quit"
        elif self.state == "game_over":
            if self.btn_retry.handle(ev):
                self.reset(); self.state="playing"; return
            if self.btn_menu2.handle(ev): self.state="menu"; return
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
        if self.flash > 0: self.flash -= dt*2.5
        if self.pulse_cd > 0: self.pulse_cd -= dt
        self.starfield.update(dt)
        for p in self.planets: p.update(dt)
        if self.state != "playing": return
        keys = pygame.key.get_pressed()
        dx = dy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if dx != 0 or dy != 0:
            n = math.hypot(dx, dy)
            self.last_input_dir = (dx/n, dy/n)
        self.ship.update(keys, dt)
        if self.dash_t > 0:
            self.dash_t -= dt
            self.ship.x += self.dash_v[0]*dt
            self.ship.y += self.dash_v[1]*dt
            self.ship.x = max(-SHIP_LIMIT_X, min(SHIP_LIMIT_X, self.ship.x))
            self.ship.y = max(-SHIP_LIMIT_Y, min(SHIP_LIMIT_Y, self.ship.y))
        if self.dash_cd > 0: self.dash_cd -= dt
        self.spawn_t += dt
        interval = max(0.35, 1.0 - self.elapsed*0.010)
        if self.spawn_t >= interval and len(self.asteroids) < 40:
            self.spawn_t = 0
            self.spawn_asteroid()
            if self.elapsed > 25 and random.random() < 0.4:
                self.spawn_asteroid()

        # Космический мусор
        if self.elapsed >= self.junk_start_at:
            self.junk_timer += dt
            junk_interval = max(0.7, 1.6 - (self.elapsed - self.junk_start_at) * 0.015)
            if self.junk_timer >= junk_interval and len(self.junk) < 15:
                self.junk_timer = 0
                self.spawn_junk()

        for a in self.asteroids: a.update(dt, self.ship)
        for j in self.junk: j.update(dt)
        for p in self.particles: p.update(dt)

        if self.ship.invuln <= 0:
            # Астероиды
            for a in self.asteroids:
                if not a.alive: continue
                dx = a.pos.x - self.ship.x; dy = a.pos.y - self.ship.y
                r_hit = a.radius + 22
                if (dx*dx + dy*dy < r_hit*r_hit) and (-180 < a.pos.z < 180):
                    self.ship.lives -= 1; self.ship.invuln = 1.5
                    a.hp -= 1; a.hit_flash = 0.3
                    if a.hp <= 0: a.alive = False
                    sp_scr = proj(self.ship.x, self.ship.y, SHIP_Z)
                    if sp_scr:
                        for _ in range(45):
                            self.particles.append(Particle(sp_scr[0], sp_scr[1]))
                    if self.ship.lives <= 0:
                        self.best = max(self.best, self.elapsed)
                        self.state = "game_over"
                    break
            # Мусор (если ещё живы и не врезались)
            if self.ship.invuln <= 0:
                for j in self.junk:
                    if not j.alive: continue
                    dx = j.pos.x - self.ship.x; dy = j.pos.y - self.ship.y
                    r_hit = j.radius + 18
                    if (dx*dx + dy*dy < r_hit*r_hit) and (-150 < j.pos.z < 150):
                        self.ship.lives -= 1; self.ship.invuln = 1.5
                        j.alive = False
                        sp_scr = proj(self.ship.x, self.ship.y, SHIP_Z)
                        if sp_scr:
                            for _ in range(30):
                                self.particles.append(
                                    Particle(sp_scr[0], sp_scr[1], (200,200,220)))
                        if self.ship.lives <= 0:
                            self.best = max(self.best, self.elapsed)
                            self.state = "game_over"
                        break

        self.asteroids = [a for a in self.asteroids
                          if a.alive and not a.is_culled()]
        self.junk = [j for j in self.junk if j.alive and not j.is_culled()]
        self.particles = [p for p in self.particles if p.life > 0]
        self.elapsed += dt

    def draw_world(self):
        screen.fill(BLACK)
        # 1. Фоновые звёзды + Солнце
        self.starfield.draw_background()
        # 2. Планеты
        for p in self.planets: p.draw()
        # 3. Сортировка: астероиды, мусор, корабль по Z
        renderables = []
        for a in self.asteroids:
            if a.pos.z > -400:
                renderables.append((a.pos.z, 0, a))
        for j in self.junk:
            if j.pos.z > -400:
                renderables.append((j.pos.z, 0, j))
        renderables.append((SHIP_Z, 1, self.ship))
        renderables.sort(key=lambda r: -r[0])
        for (_, kind, obj) in renderables:
            obj.draw()
        # 4. HP-полоски
        for a in self.asteroids: a.draw_hp()
        # 5. Динамические звёзды (1px, штрихи)
        self.starfield.draw_foreground()
        # 6. Частицы
        for p in self.particles: p.draw(screen)

    def panel(self, r, alpha=200):
        s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (*PANEL, alpha), (0,0,r.w,r.h), border_radius=10)
        screen.blit(s, r.topleft)
        pygame.draw.rect(screen, BORDER, r, 1, border_radius=10)

    def txt(self, text, font, color, x, y, center=False):
        img = font.render(text, True, color); sh = font.render(text, True, (0,0,0))
        if center:
            screen.blit(sh, sh.get_rect(center=(x+1,y+1)))
            screen.blit(img, img.get_rect(center=(x,y)))
        else:
            screen.blit(sh, sh.get_rect(topleft=(x+1,y+1)))
            screen.blit(img, img.get_rect(topleft=(x,y)))

    def draw_hud(self):
        r = pygame.Rect(15,15,200,82); self.panel(r)
        self.txt("ВРЕМЯ", self.f_xs, GREY, 30, 22)
        self.txt(f"{int(self.elapsed)} сек", self.f_m, WHITE, 30, 42)
        self.txt(f"рекорд {int(self.best)}", self.f_xs, CYAN, 30, 78)
        r2 = pygame.Rect(W//2-85,15,170,62); self.panel(r2)
        spd = 1.0 + self.elapsed*0.025
        col = YELLOW if spd<2 else (ORANGE if spd<3 else RED)
        self.txt(f"x{spd:.2f}", self.f_m, col, W//2, 32, True)
        self.txt("ТЕМП", self.f_xs, GREY, W//2, 60, True)
        r3 = pygame.Rect(W-180,15,165,62); self.panel(r3)
        self.txt("ЖИЗНИ", self.f_xs, GREY, W-165, 22)
        for i in range(3):
            cx = W-145+i*32; cy = 55
            if i < self.ship.lives:
                g = get_glow(RED, 14)
                if g: screen.blit(g, (cx-14, cy-14), special_flags=pygame.BLEND_ADD)
                pygame.draw.circle(screen, RED, (cx,cy), 8)
                pygame.draw.circle(screen, (255,220,220), (cx,cy), 8, 2)
            else:
                pygame.draw.circle(screen, (40,40,55), (cx,cy), 8)
                pygame.draw.circle(screen, (80,85,105), (cx,cy), 8, 1)
        sp = math.hypot(self.ship.vx, self.ship.vy)
        r_sp = pygame.Rect(W//2-85,80,170,30); self.panel(r_sp)
        sp_k = min(1.0, sp/self.ship.max_sp)
        bar = pygame.Rect(W//2-75,88,150,12)
        pygame.draw.rect(screen, (20,30,50), bar, border_radius=6)
        col_sp = GREEN if sp_k<0.5 else (YELLOW if sp_k<0.85 else RED)
        pygame.draw.rect(screen, col_sp, (bar.x,bar.y,int(bar.w*sp_k),bar.h), border_radius=6)
        pygame.draw.rect(screen, BORDER, bar, 1, border_radius=6)
        self.txt(f"{int(sp)}", self.f_xs, WHITE, W//2, 105, True)
        r4 = pygame.Rect(15, H-90, 200, 75); self.panel(r4)
        self.txt("РЫВОК [SHIFT]", self.f_xs, GREY, 30, H-84)
        bar = pygame.Rect(30, H-68, 170, 8)
        pygame.draw.rect(screen, (20,30,50), bar, border_radius=4)
        k = 1 - self.dash_cd/1.2 if self.dash_cd > 0 else 1
        k = max(0, min(1, k))
        if k > 0:
            c = GREEN if k>=1 else (YELLOW if k>0.4 else RED)
            pygame.draw.rect(screen, c, (bar.x,bar.y,int(bar.w*k),bar.h), border_radius=4)
        pygame.draw.rect(screen, BORDER, bar, 1, border_radius=4)
        self.txt("ИМПУЛЬС [SPACE]", self.f_xs, GREY, 30, H-48)
        bar2 = pygame.Rect(30, H-32, 170, 8)
        pygame.draw.rect(screen, (20,30,50), bar2, border_radius=4)
        k2 = 1 - self.pulse_cd/1.2 if self.pulse_cd > 0 else 1
        k2 = max(0, min(1, k2))
        if k2 > 0:
            c = CYAN if k2>=1 else (YELLOW if k2>0.4 else RED)
            pygame.draw.rect(screen, c, (bar2.x,bar2.y,int(bar2.w*k2),bar2.h), border_radius=4)
        pygame.draw.rect(screen, BORDER, bar2, 1, border_radius=4)
        self.txt("WASD движение · SPACE импульс · SHIFT рывок · ESC пауза",
                 self.f_xs, GREY, W//2, H-18, True)

    def draw_menu(self):
        screen.fill(BLACK)
        self.starfield.draw_background()
        for p in self.planets: p.draw()
        old_x, old_y = self.ship.x, self.ship.y
        self.ship.x = 0; self.ship.y = -80
        self.ship.draw()
        self.ship.x, self.ship.y = old_x, old_y
        self.starfield.draw_foreground()
        ov = pygame.Surface((W,H), pygame.SRCALPHA)
        ov.fill((0,0,15,140)); screen.blit(ov, (0,0))
        self.txt("3D HYPERFLIGHT", self.f_big, CYAN, W//2, 140, True)
        self.txt("объёмный корабль · металл и бронза · планеты СС",
                 self.f_s, GREY, W//2, 190, True)
        self.btn_play.draw(screen); self.btn_quit.draw(screen)
        if self.best > 0:
            self.txt(f"РЕКОРД  {int(self.best)} сек", self.f_m, YELLOW, W//2, H-50, True)

    def draw_pause(self):
        self.draw_world(); self.draw_hud()
        ov = pygame.Surface((W,H), pygame.SRCALPHA)
        ov.fill((0,0,15,180)); screen.blit(ov, (0,0))
        self.txt("ПАУЗА", self.f_big, YELLOW, W//2, H//2-150, True)
        self.btn_resume.draw(screen); self.btn_menu.draw(screen)
        self.btn_quit2.draw(screen)

    def draw_game_over(self):
        self.draw_world()
        ov = pygame.Surface((W,H), pygame.SRCALPHA)
        ov.fill((30,0,0,200)); screen.blit(ov, (0,0))
        self.txt("СИСТЕМА УНИЧТОЖЕНА", self.f_big, RED, W//2, H//2-160, True)
        r = pygame.Rect(W//2-200, H//2-100, 400, 120); self.panel(r, alpha=220)
        self.txt("ВРЕМЯ В 3D", self.f_xs, GREY, W//2, H//2-75, True)
        self.txt(f"{int(self.elapsed)} сек", self.f_l, WHITE, W//2, H//2-35, True)
        if int(self.elapsed) >= int(self.best):
            self.txt("★ НОВЫЙ РЕКОРД ★", self.f_s, YELLOW, W//2, H//2+15, True)
        else:
            self.txt(f"Рекорд: {int(self.best)} сек", self.f_s, CYAN, W//2, H//2+15, True)
        self.btn_retry.draw(screen); self.btn_menu2.draw(screen)

    def draw(self):
        if self.state == "menu": self.draw_menu()
        elif self.state == "playing": self.draw_world(); self.draw_hud()
        elif self.state == "paused": self.draw_pause()
        elif self.state == "game_over": self.draw_game_over()
        if self.flash > 0:
            ov = pygame.Surface((W,H), pygame.SRCALPHA)
            ov.fill((0,220,255,int(70*self.flash)))
            screen.blit(ov, (0,0), special_flags=pygame.BLEND_ADD)

# ============================================================
def main():
    g = Game(); running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for ev in pygame.event.get():
            if g.handle(ev) == "quit": running = False
        g.update(dt); g.draw()
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()