# -*- coding: utf-8 -*-
"""
4D Hyperflight — финальная версия (все баги исправлены).
"""
import pygame, math, random

pygame.init()
W, H = 1000, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("4D Hyperflight")
clock = pygame.time.Clock()
FPS = 60

BLACK=(2,3,12); WHITE=(245,250,255); CYAN=(0,220,240); YELLOW=(255,220,80)
ORANGE=(255,140,0); RED=(235,70,70); GREEN=(100,230,140); GREY=(150,155,175)
DIM=(80,90,110); PANEL=(10,15,32); BORDER=(60,95,150)
BLUE_C=(60,130,240); RED_C=(240,80,80)

SLICE_W = 25.0
SHIP_LIMIT_X = 550.0
SHIP_LIMIT_Y = 390.0

# ============================================================
#              МАТЕМАТИКА 4D
# ============================================================
class V4:
    __slots__=('x','y','z','w')
    def __init__(s,x=0.0,y=0.0,z=0.0,w=0.0):
        s.x,s.y,s.z,s.w=float(x),float(y),float(z),float(w)
    def __add__(s,o): return V4(s.x+o.x,s.y+o.y,s.z+o.z,s.w+o.w)
    def __sub__(s,o): return V4(s.x-o.x,s.y-o.y,s.z-o.z,s.w-o.w)
    def __mul__(s,k): return V4(s.x*k,s.y*k,s.z*k,s.w*k)
    __rmul__=__mul__

def rot4(v,a,p):
    c,s=math.cos(a),math.sin(a); x,y,z,w=v.x,v.y,v.z,v.w
    if p=='XY': return V4(x*c-y*s,x*s+y*c,z,w)
    if p=='XZ': return V4(x*c-z*s,y,x*s+z*c,w)
    if p=='XW': return V4(x*c-w*s,y,z,x*s+w*c)
    if p=='YZ': return V4(x,y*c-z*s,y*s+z*c,w)
    if p=='YW': return V4(x,y*c-w*s,z,y*s+w*c)
    return V4(x,y,z*c-w*s,z*s+w*c)

FOV_3D=620.0; CAM_Z=700.0
def proj(x,y,z):
    rz=z+CAM_Z
    if rz<60: return None
    k=FOV_3D/rz
    return (W/2+x*k, H/2+y*k, k, rz)

def w_color(base,w):
    t=min(1.0,abs(w)/180.0)*0.85
    tgt=BLUE_C if w<0 else RED_C
    return (int(base[0]*(1-t)+tgt[0]*t),
            int(base[1]*(1-t)+tgt[1]*t),
            int(base[2]*(1-t)+tgt[2]*t))

_glow={}
def get_glow(color,radius):
    if radius<1: return None
    key=(color[0]//16,color[1]//16,color[2]//16,radius//4)
    if key in _glow: return _glow[key]
    size=radius*2
    s=pygame.Surface((size,size),pygame.SRCALPHA)
    steps=max(4,min(12,radius//4))
    for i in range(steps,0,-1):
        r=int(radius*i/steps)
        a=int(90*(1-i/steps)**2)
        if a>0 and r>0:
            pygame.draw.circle(s,(color[0],color[1],color[2],a),(radius,radius),r)
    if len(_glow)<300: _glow[key]=s
    return s

# ============================================================
#              ПАЛИТРЫ КАМНЯ
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
    rnd=random.Random(seed)
    verts=[(0,size*rnd.uniform(0.9,1.15),0)]
    rings=[]
    for m in range(1,m_rings):
        phi=math.pi*m/m_rings
        y=size*math.cos(phi); r=size*math.sin(phi)
        ring=[]
        for n in range(n_ring):
            theta=math.tau*n/n_ring
            rr=r*rnd.uniform(1-irregularity,1+irregularity)
            yy=y*rnd.uniform(1-irregularity*0.5,1+irregularity*0.5)
            if rnd.random()<0.12: rr*=rnd.uniform(0.55,0.75)
            elif rnd.random()<0.08: rr*=rnd.uniform(1.15,1.35)
            ring.append(len(verts))
            verts.append((rr*math.cos(theta),yy,rr*math.sin(theta)))
        rings.append(ring)
    verts.append((0,-size*rnd.uniform(0.85,1.15),0))
    south=len(verts)-1
    faces=[]
    for n in range(n_ring): faces.append([0,rings[0][(n+1)%n_ring],rings[0][n]])
    for m in range(len(rings)-1):
        for n in range(n_ring):
            a=rings[m][n]; b=rings[m][(n+1)%n_ring]
            c=rings[m+1][(n+1)%n_ring]; d=rings[m+1][n]
            faces.append([a,b,c,d])
    for n in range(n_ring):
        faces.append([south,rings[-1][n],rings[-1][(n+1)%n_ring]])
    return verts, faces

# ============================================================
#              ТРАЕКТОРИИ
# ============================================================
TRAJ_STRAIGHT = 0
TRAJ_WAVE     = 1
TRAJ_SPIRAL   = 2
TRAJ_ZIGZAG   = 3
TRAJ_ORBITAL  = 4

# ============================================================
#              АСТЕРОИД / МЕТЕОРИТ
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

    def __init__(self, pos, seed, kind=None, vel_hint=None):
        if kind is None:
            kinds=list(self.KINDS.keys())
            weights=[self.KINDS[k]['spawn_weight'] for k in kinds]
            kind=random.choices(kinds,weights=weights)[0]
        self.kind=kind; cfg=self.KINDS[kind]
        rnd=random.Random(seed); self.seed=seed
        size=rnd.uniform(*cfg['size']); self.scale=size
        self.verts, self.faces = make_rock_mesh(size, seed,
                                                cfg['n_ring'], cfg['m_rings'],
                                                cfg['irregularity'])
        self.hp=cfg['hp']; self.max_hp=cfg['hp']; self.hit_flash=0.0
        pal_name=rnd.choice(cfg['palettes']); self.palette_name=pal_name
        pal=ROCK_PALETTES[pal_name]
        self.specular=pal['specular']
        self.vein_colors = pal['vein_colors']
        self.face_colors=[rnd.choice(pal['shades']) for _ in self.faces]
        # Кратеры
        n_craters=rnd.randint(*cfg['craters'])
        self.crater_faces={}
        for _ in range(n_craters):
            fi=rnd.randrange(len(self.faces))
            self.crater_faces[fi]={'depth':rnd.uniform(0.42,0.68)}
        # Царапины
        n_scr=rnd.randint(*cfg['scratches'])
        self.scratches=[]
        for _ in range(n_scr):
            theta=rnd.uniform(0,math.tau); phi=rnd.uniform(0.35,math.pi*0.65)
            r=size*0.95
            x1=r*math.sin(phi)*math.cos(theta); y1=r*math.cos(phi)
            z1=r*math.sin(phi)*math.sin(theta)
            dth=rnd.uniform(-0.85,0.85); dph=rnd.uniform(-0.55,0.55)
            x2=r*math.sin(phi+dph)*math.cos(theta+dth); y2=r*math.cos(phi+dph)
            z2=r*math.sin(phi+dph)*math.sin(theta+dth)
            self.scratches.append(((x1,y1,z1),(x2,y2,z2)))
        # Прожилки
        n_veins=rnd.randint(*cfg['veins'])
        self.veins=[]
        for _ in range(n_veins):
            theta=rnd.uniform(0,math.tau); phi=rnd.uniform(0.3,math.pi*0.7)
            pts=[]
            for k in range(3):
                t = k/2
                a = theta + t*rnd.uniform(-0.6, 0.6)
                p = phi + t*rnd.uniform(-0.5, 0.5)
                rv = size * 0.92
                px = rv*math.sin(p)*math.cos(a)
                py = rv*math.cos(p)
                pz = rv*math.sin(p)*math.sin(a)
                pts.append((px,py,pz))
            self.veins.append({'points':pts, 'color':rnd.choice(self.vein_colors)})
        # Питтинг
        self.pit_faces = {}
        for _ in range(rnd.randint(3, 8)):
            fi=rnd.randrange(len(self.faces))
            self.pit_faces[fi] = rnd.uniform(0.78, 0.92)
        # Траектория
        self.trajectory = rnd.choice([TRAJ_STRAIGHT, TRAJ_WAVE, TRAJ_SPIRAL,
                                       TRAJ_ZIGZAG, TRAJ_ORBITAL])
        self.traj_time = rnd.uniform(0, 10)
        self.traj_param = rnd.uniform(0.6, 1.6)
        self.pos=pos
        self.rx=rnd.uniform(0,math.tau); self.ry=rnd.uniform(0,math.tau)
        self.rz=rnd.uniform(0,math.tau)
        self.rvx=rnd.uniform(-0.4,0.4); self.rvy=rnd.uniform(-0.4,0.4)
        self.rvz=rnd.uniform(-0.4,0.4)
        if vel_hint is not None:
            self.vel=vel_hint
        else:
            sp=rnd.uniform(*cfg['speed'])
            self.vel=V4(rnd.uniform(-80,80),rnd.uniform(-80,80),
                        -sp,rnd.uniform(-40,40))
        self.radius=size*1.3; self.alive=True
        self.homing=False

    def rotate_vertex(self,v):
        x,y,z=v
        cx,sx=math.cos(self.rx),math.sin(self.rx)
        y1=y*cx-z*sx; z1=y*sx+z*cx; x1=x
        cy,sy=math.cos(self.ry),math.sin(self.ry)
        x2=x1*cy+z1*sy; z2=-x1*sy+z1*cy; y2=y1
        cz,sz=math.cos(self.rz),math.sin(self.rz)
        return (x2*cz-y2*sz, x2*sz+y2*cz, z2)

    def update(self,dt,ship):
        self.traj_time += dt
        if self.trajectory == TRAJ_WAVE:
            perp_x = -self.vel.y; perp_y = self.vel.x
            pl = math.sqrt(perp_x**2 + perp_y**2) or 1
            perp_x /= pl; perp_y /= pl
            offset = math.sin(self.traj_time * 2.5 * self.traj_param) * 45
            self.pos.x += perp_x * offset * dt
            self.pos.y += perp_y * offset * dt
        elif self.trajectory == TRAJ_SPIRAL:
            ang = self.traj_param * dt * 1.8
            ca, sa = math.cos(ang), math.sin(ang)
            vx = self.vel.x * ca - self.vel.y * sa
            vy = self.vel.x * sa + self.vel.y * ca
            self.vel.x = vx; self.vel.y = vy
        elif self.trajectory == TRAJ_ZIGZAG:
            if int(self.traj_time * 3) % 2 == 0:
                self.pos.x += math.sin(self.traj_time * 5) * 30 * dt
        elif self.trajectory == TRAJ_ORBITAL:
            ang = self.traj_param * dt * 0.6
            ca, sa = math.cos(ang), math.sin(ang)
            vx = self.vel.x * ca - self.vel.z * sa
            vz = self.vel.x * sa + self.vel.z * ca
            self.vel.x = vx; self.vel.z = vz

        if getattr(self, 'homing', False) and self.pos.z > 60:
            dx = ship.x - self.pos.x; dy = ship.y - self.pos.y; dz = -self.pos.z
            d = math.sqrt(dx*dx + dy*dy + dz*dz) or 1.0
            sp = math.sqrt(self.vel.x**2 + self.vel.y**2 + self.vel.z**2) or 300
            tx = dx / d * sp; ty = dy / d * sp; tz = dz / d * sp
            k = min(1.0, 1.6 * dt)
            self.vel.x += (tx - self.vel.x) * k
            self.vel.y += (ty - self.vel.y) * k
            self.vel.z += (tz - self.vel.z) * k
        elif random.random() < 0.02:
            dx = ship.x - self.pos.x; dy = ship.y - self.pos.y
            L = math.hypot(dx, dy) + 1e-6
            self.vel.x += (dx / L) * 40 * dt
            self.vel.y += (dy / L) * 40 * dt

        self.pos=self.pos+self.vel*dt
        self.rx+=self.rvx*dt; self.ry+=self.rvy*dt; self.rz+=self.rvz*dt
        if self.hit_flash>0: self.hit_flash=max(0,self.hit_flash-dt*3)
        if self.pos.z < -2000 or self.pos.z > 7000: self.alive=False
        if abs(self.pos.x) > 8000 or abs(self.pos.y) > 8000: self.alive=False
        if abs(self.pos.w) > 5000: self.alive=False

    def get_world_pos(self,wr):
        p=self.pos
        for pl in ('XW','YW','ZW'):
            if abs(wr[pl])>1e-6:
                p=rot4(p,wr[pl],pl)
        return p

    def draw(self,wr):
        wp=self.get_world_pos(wr)
        screen_v=[]; world_v=[]
        for vert in self.verts:
            rv=self.rotate_vertex(vert)
            wx=wp.x+rv[0]; wy=wp.y+rv[1]; wz=wp.z+rv[2]
            world_v.append((wx,wy,wz))
            screen_v.append(proj(wx,wy,wz))
        face_data=[]
        for fi,face in enumerate(self.faces):
            pts=[]; valid=True; z_sum=0.0
            for idx in face:
                p=screen_v[idx]
                if p is None: valid=False; break
                pts.append((int(p[0]),int(p[1]))); z_sum+=p[3]
            if not valid or len(pts)<3: continue
            n=len(face); z_avg=z_sum/n
            i0,i1,i2=face[0],face[1],face[2]
            a=world_v[i0]; b=world_v[i1]; c=world_v[i2]
            ux=b[0]-a[0]; uy=b[1]-a[1]; uz=b[2]-a[2]
            vx=c[0]-a[0]; vy=c[1]-a[1]; vz=c[2]-a[2]
            nx=uy*vz-uz*vy; ny=uz*vx-ux*vz; nz=ux*vy-uy*vx
            nl=math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0
            nx/=nl; ny/=nl; nz/=nl
            lx,ly,lz=-0.35,-0.55,-0.75
            dot=nx*lx+ny*ly+nz*lz
            light=0.42+0.58*abs(dot); light*=0.85+0.15*max(0,-ny)
            base=self.face_colors[fi]
            if fi in self.crater_faces:
                k = self.crater_faces[fi]['depth']
                base = (int(base[0]*k), int(base[1]*k), int(base[2]*k))
            if fi in self.pit_faces:
                k = self.pit_faces[fi]
                base = (int(base[0]*k), int(base[1]*k), int(base[2]*k))
            if self.hit_flash>0:
                fb=self.hit_flash/0.3
                base=(min(255,int(base[0]+220*fb)),
                      min(255,int(base[1]+100*fb)),
                      min(255,int(base[2]+100*fb)))
            col=(min(255,int(base[0]*light)),
                 min(255,int(base[1]*light)),
                 min(255,int(base[2]*light)))
            rnd_local = (fi * 2654435761) & 0xFFFFFFFF
            speckle = (rnd_local % 11) - 5
            col = (max(0, min(255, col[0] + speckle)),
                   max(0, min(255, col[1] + speckle)),
                   max(0, min(255, col[2] + speckle)))
            if self.specular>0:
                d2=dot*dot; spec=max(0,d2*d2*d2)*self.specular
                col=(min(255,int(col[0]+spec*220)),
                     min(255,int(col[1]+spec*220)),
                     min(255,int(col[2]+spec*230)))
            col=w_color(col,wp.w)
            face_data.append((z_avg,pts,col,wp.w))
        face_data.sort(key=lambda f:-f[0])
        for (_,pts,col,w) in face_data:
            pygame.draw.polygon(screen,col,pts)
            if abs(w)<SLICE_W:
                glow=(min(255,col[0]+70),min(255,col[1]+50),min(255,col[2]+30))
                pygame.draw.polygon(screen,glow,pts,2)
            else:
                pygame.draw.polygon(screen,(0,0,0),pts,1)
        self._draw_veins(wp)
        self._draw_scratches(wp)
        # BUGFIX: HP-полоска — только если в срезе
        if self.hp<self.max_hp and abs(wp.w) < SLICE_W * 2:
            self._draw_hp(wp)

    def _draw_veins(self, wp):
        cdx=-wp.x; cdy=-wp.y; cdz=-wp.z-CAM_Z
        cl=math.sqrt(cdx*cdx+cdy*cdy+cdz*cdz) or 1
        cdx/=cl; cdy/=cl; cdz/=cl
        for vein in self.veins:
            pts = []
            visible = True
            for p in vein['points']:
                rv = self.rotate_vertex(p)
                wx = wp.x + rv[0]; wy = wp.y + rv[1]; wz = wp.z + rv[2]
                mx = wx - wp.x; my = wy - wp.y; mz = wz - wp.z
                ml = math.sqrt(mx*mx+my*my+mz*mz) or 1
                if (mx/ml)*cdx + (my/ml)*cdy + (mz/ml)*cdz < 0.15:
                    visible = False
                    break
                sp = proj(wx, wy, wz)
                if sp is None:
                    visible = False
                    break
                pts.append((int(sp[0]), int(sp[1]), sp[3]))
            if not visible or len(pts) < 2:
                continue
            col = vein['color']
            lw = max(1, min(3, int(2.0 * pts[0][2] / 600)))
            for i in range(len(pts) - 1):
                x1,y1,_ = pts[i]
                x2,y2,_ = pts[i+1]
                pygame.draw.line(screen, col, (x1,y1), (x2,y2), lw)
                glow_col = (min(255, col[0]+40), min(255, col[1]+40),
                            min(255, col[2]+30))
                pygame.draw.line(screen, glow_col, (x1,y1), (x2,y2), 1)

    def _draw_scratches(self,wp):
        cdx=-wp.x; cdy=-wp.y; cdz=-wp.z-CAM_Z
        cl=math.sqrt(cdx*cdx+cdy*cdy+cdz*cdz) or 1
        cdx/=cl; cdy/=cl; cdz/=cl
        for (p1,p2) in self.scratches:
            rv1=self.rotate_vertex(p1); rv2=self.rotate_vertex(p2)
            wx1=wp.x+rv1[0]; wy1=wp.y+rv1[1]; wz1=wp.z+rv1[2]
            wx2=wp.x+rv2[0]; wy2=wp.y+rv2[1]; wz2=wp.z+rv2[2]
            mx=(wx1+wx2)*0.5-wp.x; my=(wy1+wy2)*0.5-wp.y; mz=(wz1+wz2)*0.5-wp.z
            ml=math.sqrt(mx*mx+my*my+mz*mz) or 1
            if (mx/ml)*cdx+(my/ml)*cdy+(mz/ml)*cdz<0.25: continue
            sp1=proj(wx1,wy1,wz1); sp2=proj(wx2,wy2,wz2)
            if sp1 is None or sp2 is None: continue
            dk=600/max(80,sp1[3])
            lw=max(1,int(1.6*dk))
            shade=max(20,min(90,int(50*dk)))
            pygame.draw.line(screen,(shade,shade,shade),
                             (int(sp1[0]),int(sp1[1])),
                             (int(sp2[0]),int(sp2[1])),lw)

    def _draw_hp(self,wp):
        p=proj(wp.x,wp.y-self.radius*1.4,wp.z)
        if p is None: return
        sx,sy,k,rz=p
        if rz>1800: return
        w=int(50*k); h=max(2,int(5*k))
        if w<8: return
        x=int(sx-w/2); y=int(sy-h/2)
        pygame.draw.rect(screen,(60,20,20),(x,y,w,h))
        ratio=self.hp/self.max_hp
        col=(220,200,60) if ratio>0.6 else ((240,140,40) if ratio>0.3 else (235,60,60))
        pygame.draw.rect(screen,col,(x,y,int(w*ratio),h))
        pygame.draw.rect(screen,(180,200,230),(x,y,w,h),1)

# ============================================================
#              КОРАБЛЬ
# ============================================================
class Ship:
    SECTIONS = [
        (64,  1.5,  2.5,  2.5), (50,  4.5,  6.0,  5.0),
        (36,  7.5,  8.0,  7.0), (18, 10.5,  9.0,  8.5),
        (-2, 10.5,  9.0,  8.5), (-20, 8.0,  7.5,  7.0),
        (-32, 5.5,  6.0,  5.5), (-40, 4.0,  5.0,  4.5),
    ]

    SKELETON = [
        (0, 0, 64, 0, 0, -40),
        (0, 0, 50, -9, 0, 50), (0, 0, 50, 9, 0, 50),
        (0, 0, 36, -14, 0, 36), (0, 0, 36, 14, 0, 36),
        (0, 0, 18, -18, 0, 18), (0, 0, 18, 18, 0, 18),
        (0, 0, -2, -18, 0, -2), (0, 0, -2, 18, 0, -2),
        (0, 0, -20, -15, 0, -20), (0, 0, -20, 15, 0, -20),
        (0, 0, -32, -11, 0, -32), (0, 0, -32, 11, 0, -32),
        (-9, 0, 50, -14, 0, 36), (-14, 0, 36, -18, 0, 18),
        (-18, 0, 18, -18, 0, -2), (-18, 0, -2, -15, 0, -20),
        (-15, 0, -20, -11, 0, -32),
        (9, 0, 50, 14, 0, 36), (14, 0, 36, 18, 0, 18),
        (18, 0, 18, 18, 0, -2), (18, 0, -2, 15, 0, -20),
        (15, 0, -20, 11, 0, -32),
    ]

    MATERIALS = {
        'white':    {'base':(218, 224, 236), 'spec_color':(255, 255, 255),
                     'spec_strength':0.55, 'spec_power':26,
                     'ambient':0.36, 'rim_color':(200, 230, 255),
                     'rim_strength':0.35},
        'white_d':  {'base':(158, 168, 188), 'spec_color':(220, 240, 255),
                     'spec_strength':0.45, 'spec_power':20,
                     'ambient':0.28, 'rim_color':(160, 200, 240),
                     'rim_strength':0.32},
        'bronze':   {'base':(205, 140, 75),  'spec_color':(255, 220, 150),
                     'spec_strength':0.95, 'spec_power':48,
                     'ambient':0.30, 'rim_color':(255, 200, 110),
                     'rim_strength':0.60},
        'bronze_d': {'base':(130, 80, 40),   'spec_color':(255, 180, 100),
                     'spec_strength':0.80, 'spec_power':36,
                     'ambient':0.26, 'rim_color':(220, 140, 70),
                     'rim_strength':0.45},
        'glass':    {'base':(38, 90, 165),   'spec_color':(220, 245, 255),
                     'spec_strength':1.00, 'spec_power':90,
                     'ambient':0.45, 'rim_color':(140, 200, 255),
                     'rim_strength':0.70},
    }

    ENGINES = [(-7, -2, -42), (7, -2, -42), (0, -5, -42)]
    _LIGHT = None
    _HULL_PLATES = None

    @classmethod
    def _build_hull(cls):
        if cls._HULL_PLATES is not None:
            return cls._HULL_PLATES
        plates = []
        secs = []
        for (z, hw, ty, by) in cls.SECTIONS:
            secs.append([(-hw,  ty, z), ( hw,  ty, z),
                         ( hw, -by, z), (-hw, -by, z)])
        nose = (0, 0, 70); s0 = secs[0]
        plates.append(([nose, s0[0], s0[1]], 'bronze',   'up'))
        plates.append(([nose, s0[1], s0[2]], 'bronze_d', 'right'))
        plates.append(([nose, s0[2], s0[3]], 'bronze_d', 'down'))
        plates.append(([nose, s0[3], s0[0]], 'bronze',   'left'))
        for i in range(len(secs) - 1):
            z_mid = (cls.SECTIONS[i][0] + cls.SECTIONS[i+1][0]) * 0.5
            if z_mid > 38 or z_mid < -20:
                mt, ms = 'bronze', 'bronze_d'
            else:
                mt, ms = 'white', 'white_d'
            A = secs[i]; B = secs[i+1]
            plates.append(([A[0], A[1], B[1], B[0]], mt, 'up'))
            plates.append(([A[1], A[2], B[2], B[1]], ms, 'right'))
            plates.append(([A[3], B[3], B[2], A[2]], ms, 'down'))
            plates.append(([A[0], B[0], B[3], A[3]], ms, 'left'))
        sN = secs[-1]
        plates.append(([sN[0], sN[1], sN[2], sN[3]], 'bronze_d', 'back'))
        plates.append(([(-5.5, 9.2, 46), (5.5, 9.2, 46),
                        (7.0, 9.2, 30), (-7.0, 9.2, 30)], 'glass', 'up'))
        cab_pts = [(-5.5, 9.2, 46), (5.5, 9.2, 46),
                   (7.0, 9.2, 30), (-7.0, 9.2, 30)]
        cab_bot = [(-5.5, 8.0, 46), (5.5, 8.0, 46),
                   (7.0, 7.8, 30), (-7.0, 7.8, 30)]
        for k in range(4):
            a = cab_pts[k]; b = cab_pts[(k+1) % 4]
            a2 = cab_bot[k]; b2 = cab_bot[(k+1) % 4]
            plates.append(([a, b, b2, a2], 'bronze_d', None))
        for side in (-1, 1):
            x_r = 10.0 * side; x_t = 46.0 * side
            top = [(x_r, 0.8, 14), (x_t, 0.3, -10),
                   (x_t, 0.3, -30), (x_r, 0.8, -22)]
            bot = [(x, -0.8, z) for (x, y, z) in top]
            plates.append((top, 'white',   'up'))
            plates.append((list(reversed(bot)), 'white_d', 'down'))
            for k in range(4):
                a = top[k]; b = top[(k+1) % 4]
                a2 = bot[k]; b2 = bot[(k+1) % 4]
                hint = None
                if k == 0:   hint = 'front'
                elif k == 2: hint = 'back'
                elif k == 1: hint = 'right' if side > 0 else 'left'
                plates.append(([a, b, b2, a2], 'bronze_d', hint))
            tip = [(x_t, 0.3, -10), (x_t, 0.3, -30),
                   (x_t, -0.8, -30), (x_t, -0.8, -10)]
            plates.append((tip, 'bronze', 'right' if side > 0 else 'left'))
        cls._HULL_PLATES = plates
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
        rx = x * cr - y * sr
        ry = x * sr + y * cr
        return (self.x + rx, self.y + ry, z)

    @classmethod
    def _plate_normal(cls, points, cr, sr, hint=None):
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
        nx2 = nx * cr - ny * sr
        ny2 = nx * sr + ny * cr
        return (nx2, ny2, nz)

    @classmethod
    def _lighting(cls, normal, mat_key):
        if cls._LIGHT is None:
            lx, ly, lz = -0.42, -0.58, -0.70
            L = math.sqrt(lx*lx + ly*ly + lz*lz)
            cls._LIGHT = (lx/L, ly/L, lz/L)
        LX, LY, LZ = cls._LIGHT
        VX, VY, VZ = 0.0, 0.0, -1.0
        nx, ny, nz = normal
        diff = max(0.0, nx*LX + ny*LY + nz*LZ)
        hx = LX+VX; hy = LY+VY; hz = LZ+VZ
        hl = math.sqrt(hx*hx + hy*hy + hz*hz) or 1.0
        hx /= hl; hy /= hl; hz /= hl
        spec_dot = max(0.0, nx*hx + ny*hy + nz*hz)
        mat = cls.MATERIALS[mat_key]
        spec = (spec_dot ** mat['spec_power']) * mat['spec_strength']
        view_dot = abs(nx*VX + ny*VY + nz*VZ)
        rim = ((1.0 - view_dot) ** 2.5) * mat['rim_strength']
        base = mat['base']; sc = mat['spec_color']; rc = mat['rim_color']
        amb = mat['ambient']
        lit = amb + (1.0 - amb) * diff
        r = base[0]*lit + sc[0]*spec + rc[0]*rim
        g = base[1]*lit + sc[1]*spec + rc[1]*rim
        b = base[2]*lit + sc[2]*spec + rc[2]*rim
        return (min(255, int(r)), min(255, int(g)), min(255, int(b)))

    def draw(self):
        s = self
        cr, sr = math.cos(s.roll), math.sin(s.roll)
        sp = math.hypot(s.vx, s.vy)

        # === 1. Свечение двигателей ===
        pulse = 0.7 + 0.3 * math.sin(s.engine_pulse)
        speed_k = max(0.3, sp / s.max_sp)
        for (ex, ey, ez) in self.ENGINES:
            wx, wy, wz = s._tx(ex, ey, ez, cr, sr)
            p = proj(wx, wy, wz)
            if p is None: continue
            sx, sy, k, rz = p
            fr = int(42 * k * pulse * speed_k)
            if fr < 3: continue
            for col, sz, alpha in [(ORANGE, fr, 130),
                                    (YELLOW, int(fr*0.75), 190),
                                    (WHITE, int(fr*0.45), 255)]:
                if sz < 1: continue
                g = get_glow(col, sz)
                if g:
                    tmp = g.copy()
                    tmp.set_alpha(alpha)
                    screen.blit(tmp, (int(sx)-sz, int(sy)-sz),
                                special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(screen, (255, 245, 220),
                               (int(sx), int(sy)), max(1, fr//4))

        # === 2. Скелет ===
        skel_col = (35, 42, 58)
        for (x1, y1, z1, x2, y2, z2) in self.SKELETON:
            wx1, wy1, wz1 = s._tx(x1, y1, z1, cr, sr)
            wx2, wy2, wz2 = s._tx(x2, y2, z2, cr, sr)
            p1 = proj(wx1, wy1, wz1); p2 = proj(wx2, wy2, wz2)
            if p1 is None or p2 is None: continue
            lw = max(1, min(3, int(2.4 * (p1[2] + p2[2]) / 2)))
            pygame.draw.line(screen, skel_col,
                             (int(p1[0]), int(p1[1])),
                             (int(p2[0]), int(p2[1])), lw)

        # BUGFIX: мерцание скрывает ВСЕ детали корабля, а не только панели
        flashing = (s.invuln > 0 and int(s.invuln * 12) % 2 == 0)
        if not flashing:
            # === 3. Панели корпуса ===
            plates = []
            for plate in Ship._HULL_PLATES:
                if len(plate) == 3:
                    points, mat_key, hint = plate
                else:
                    points, mat_key = plate
                    hint = None
                proj_pts = []
                valid = True; z_sum = 0.0
                for (px, py, pz) in points:
                    wx, wy, wz = s._tx(px, py, pz, cr, sr)
                    p = proj(wx, wy, wz)
                    if p is None: valid = False; break
                    proj_pts.append((int(p[0]), int(p[1])))
                    z_sum += p[3]
                if not valid or len(proj_pts) < 3: continue
                z_avg = z_sum / len(proj_pts)
                normal = Ship._plate_normal(points, cr, sr, hint)
                col = Ship._lighting(normal, mat_key)
                plates.append((z_avg, proj_pts, col, mat_key))
            plates.sort(key=lambda f: -f[0])
            for (_, pts, col, mat_key) in plates:
                pygame.draw.polygon(screen, col, pts)
                edge = (int(col[0]*0.5), int(col[1]*0.5), int(col[2]*0.5))
                pygame.draw.polygon(screen, edge, pts, 1)
                if mat_key in ('bronze', 'glass'):
                    pygame.draw.polygon(screen,
                        (min(255, col[0]+45), min(255, col[1]+40),
                         min(255, col[2]+30)), pts, 1)

            # === 4. Заклёпки ===
            rivets = [(-6,9.3,24),(6,9.3,24),(-6,9.3,8),(6,9.3,8),
                      (-6,9.3,-8),(6,9.3,-8),(-5,9.3,-22),(5,9.3,-22),
                      (-22,1.3,-14),(-30,1.3,-18),(22,1.3,-14),(30,1.3,-18)]
            for (rx, ry, rz) in rivets:
                wx, wy, wz = s._tx(rx, ry, rz, cr, sr)
                p = proj(wx, wy, wz)
                if p is None: continue
                d = max(1, min(3, int(p[2] * 0.9)))
                pygame.draw.circle(screen, (30, 25, 20),
                                   (int(p[0]+d*0.4), int(p[1]+d*0.4)), d)
                pygame.draw.circle(screen, (140, 118, 88),
                                   (int(p[0]), int(p[1])), d)
                if d >= 2:
                    pygame.draw.circle(screen, (225, 205, 170),
                                       (int(p[0]-d*0.4), int(p[1]-d*0.4)),
                                       max(1, d-2))

            # === 5. PBR-блик на стекле кабины ===
            glass_center_x = -s.roll * 0.08
            cab_p = proj(*s._tx(glass_center_x, 9.35, 38.0, cr, sr))
            if cab_p:
                sx, sy, k, rz = cab_p
                base_r = max(3, int(7 * k))
                for scale, alpha, tint in ((1.8, 40, (150, 200, 245)),
                                            (1.1, 90, (180, 225, 250)),
                                            (0.55, 150, (220, 240, 255))):
                    rr = max(1, int(base_r * scale))
                    g = get_glow(tint, rr)
                    if g:
                        tmp = g.copy()
                        tmp.set_alpha(alpha)
                        screen.blit(tmp, (int(sx) - rr, int(sy) - rr),
                                    special_flags=pygame.BLEND_ADD)
                ring_r = max(2, int(base_r * 0.9))
                ring_surf = pygame.Surface((ring_r * 2, ring_r * 2),
                                            pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (200, 230, 255, 90),
                                   (ring_r, ring_r), ring_r, 1)
                screen.blit(ring_surf, (int(sx) - ring_r, int(sy) - ring_r),
                            special_flags=pygame.BLEND_ADD)

# ============================================================
#              ПЛАНЕТЫ СОЛНЕЧНОЙ СИСТЕМЫ
# ============================================================
class SolarPlanet:
    DATA = {
        'mercury': {'colors':((170,165,155),(115,110,105),(215,210,200)),
                    'spot':(85,80,75),'type':'rocky','size':(180,260)},
        'venus':   {'colors':((235,205,135),(180,140,70),(255,245,205)),
                    'spot':(255,230,175),'type':'cloudy','size':(220,320)},
        'earth':   {'colors':((65,120,200),(25,65,150),(130,195,245)),
                    'spot':(90,150,80),'type':'earth','size':(220,320)},
        'mars':    {'colors':((200,110,70),(140,60,40),(240,160,110)),
                    'spot':(85,45,35),'type':'mars','size':(180,260)},
        'jupiter': {'colors':((210,180,140),(150,110,70),(245,215,180)),
                    'spot':(190,90,70),'type':'gas','size':(420,620)},
        'saturn':  {'colors':((230,210,160),(175,155,110),(250,240,210)),
                    'spot':(200,180,130),'type':'ring','size':(380,540)},
        'uranus':  {'colors':((160,220,230),(110,170,190),(215,250,255)),
                    'spot':(140,200,220),'type':'gas','size':(220,320)},
        'neptune': {'colors':((70,110,200),(40,70,150),(120,170,230)),
                    'spot':(50,80,160),'type':'gas','size':(220,320)},
    }
    ORDER = ['mercury','venus','earth','mars','jupiter','saturn','uranus','neptune']
    _idx = 0

    def __init__(self):
        kind = SolarPlanet.ORDER[SolarPlanet._idx % 8]
        SolarPlanet._idx += 1
        d = self.DATA[kind]
        self.kind = kind
        self.colors = d['colors']; self.spot_color = d['spot']
        self.planet_type = d['type']
        self.x = random.uniform(-3000, 3000)
        self.y = random.uniform(-2000, 2000)
        self.z = random.uniform(5500, 9000)
        self.size = random.uniform(*d['size'])
        self.speed_z = -random.uniform(30, 70)
        self.rotation = random.uniform(0, math.tau)
        self.rot_speed = random.uniform(-0.25, 0.25)
        self.spots = self._generate_spots()
        self.bands = self._generate_bands()
        self.clouds = self._generate_clouds()
        self.storms = self._generate_storms()
        self.cloud_offset = 0.0
        self.storm_phase = 0.0

    def _generate_spots(self):
        rnd = random.Random(hash(self.kind) + int(self.x))
        spots = []
        n = {'rocky':14,'cloudy':0,'earth':10,'mars':12,'gas':0,'ring':0}.get(self.planet_type, 0)
        for _ in range(n):
            spots.append((rnd.uniform(0, math.tau), rnd.uniform(-1.1, 1.1),
                          rnd.uniform(0.06, 0.20), rnd.uniform(0.7, 1.0)))
        return spots

    def _generate_bands(self):
        rnd = random.Random(hash(self.kind) + 42)
        bands = []
        for i in range(16):
            t = (i + 0.5) / 16
            width = rnd.uniform(0.7, 1.4) / 16
            bands.append((t, width, rnd.choice([0, 0, 1, 2]), rnd.uniform(0.7, 1.1)))
        return bands

    def _generate_clouds(self):
        if self.planet_type not in ('cloudy', 'earth'): return []
        rnd = random.Random(hash(self.kind) + 777)
        n = 14 if self.planet_type == 'cloudy' else 8
        return [(rnd.uniform(0, math.tau), rnd.uniform(-1.0, 1.0),
                 rnd.uniform(0.10, 0.28)) for _ in range(n)]

    def _generate_storms(self):
        rnd = random.Random(hash(self.kind) + 999)
        storms = []
        if self.planet_type in ('gas', 'ring'):
            n = 5 if self.kind == 'jupiter' else 3
            for _ in range(n):
                storms.append({
                    'lon': rnd.uniform(0, math.tau),
                    'lat': rnd.uniform(-0.7, 0.7),
                    'size': rnd.uniform(0.06, 0.14),
                    'color': rnd.choice([(240,240,240),(230,200,160),
                                          (200,100,80),(180,90,60)]),
                    'phase': rnd.uniform(0, math.tau),
                })
        return storms

    def update(self, dt):
        self.z += self.speed_z * dt
        self.rotation += self.rot_speed * dt
        self.cloud_offset += 0.05 * dt
        self.storm_phase += 0.4 * dt
        if self.z < 300: self.__init__()

    def _sphere_xy(self, lon, lat, r, cx, cy):
        x3 = math.cos(lat) * math.sin(lon + self.rotation)
        y3 = math.sin(lat)
        z3 = math.cos(lat) * math.cos(lon + self.rotation)
        if z3 <= 0: return None
        return (cx + x3 * r, cy - y3 * r, z3)

    def draw(self):
        p = proj(self.x, self.y, self.z)
        if p is None: return
        sx, sy, k, rz = p
        r = int(self.size * k)
        if r < 6 or r > 2200: return
        base, dark, light = self.colors
        cx = int(sx); cy = int(sy)

        # BUGFIX: кольцо — сначала задняя половина (ЗА планетой)
        if self.planet_type == 'ring':
            self._draw_ring(cx, cy, r, half='back')

        # Базовый диск
        steps = max(12, min(28, r // 4))
        for i in range(steps, 0, -1):
            t = i / steps
            if t < 0.35:
                kk = t / 0.35
                col = (int(light[0]*(1-kk) + base[0]*kk),
                       int(light[1]*(1-kk) + base[1]*kk),
                       int(light[2]*(1-kk) + base[2]*kk))
            elif t < 0.72:
                kk = (t - 0.35) / 0.37
                col = (int(base[0]*(1-kk) + dark[0]*kk),
                       int(base[1]*(1-kk) + dark[1]*kk),
                       int(base[2]*(1-kk) + dark[2]*kk))
            else:
                kk = (t - 0.72) / 0.28
                col = (int(dark[0]*(1-kk*0.5)),
                       int(dark[1]*(1-kk*0.5)),
                       int(dark[2]*(1-kk*0.5)))
            off_x = int(r * 0.12 * (1 - t))
            off_y = int(r * 0.14 * (1 - t))
            # BUGFIX: max(1, ...) — избегаем ошибки при radius=0
            pygame.draw.circle(screen, col, (cx - off_x, cy - off_y),
                               max(1, int(r * t)))

        # Поверхность
        planet_surf = pygame.Surface((r*2 + 4, r*2 + 4), pygame.SRCALPHA)
        pcx, pcy = r + 2, r + 2
        pygame.draw.circle(planet_surf, base, (pcx, pcy), r)
        self._draw_surface(planet_surf, pcx, pcy, r)
        mask = pygame.Surface((r*2 + 4, r*2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255,255,255,255), (pcx, pcy), r)
        planet_surf.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(planet_surf, (cx - pcx, cy - pcy))

        # Терминатор
        term = pygame.Surface((r*2 + 4, r*2 + 4), pygame.SRCALPHA)
        for i in range(steps):
            t = i / steps
            off_x = int(r * (0.25 + t * 0.75))
            off_y = int(r * (0.20 + t * 0.60))
            rad = int(r * (1.0 - t * 0.15))
            alpha = int(150 * (1 - t) * t * 4)
            if alpha > 0 and rad > 0:
                pygame.draw.circle(term, (0, 0, 0, alpha),
                                   (pcx + off_x, pcy + off_y), rad)
        term.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(term, (cx - pcx, cy - pcy))

        # Атмосфера
        atmo = pygame.Surface((r*2 + 40, r*2 + 40), pygame.SRCALPHA)
        acx = acy = r + 20
        for i in range(6, 0, -1):
            rr = r + i * 3
            off_x = -int(i * 1.2); off_y = -int(i * 1.4)
            alpha = int(38 * (1 - i/6))
            if alpha > 0 and rr > 0:
                pygame.draw.circle(atmo, (*light, alpha),
                                   (acx + off_x, acy + off_y), rr)
        inner_mask = pygame.Surface((r*2 + 40, r*2 + 40), pygame.SRCALPHA)
        pygame.draw.circle(inner_mask, (255,255,255,255), (acx, acy), r)
        atmo.blit(inner_mask, (0,0), special_flags=pygame.BLEND_RGBA_SUB)
        screen.blit(atmo, (cx - acx, cy - acy))

        # BUGFIX: кольцо — передняя половина (ПЕРЕД планетой)
        if self.planet_type == 'ring':
            self._draw_ring(cx, cy, r, half='front')

        # Блик
        hl_x = cx - int(r * 0.42); hl_y = cy - int(r * 0.42)
        hl_r = max(3, r // 6)
        for i in range(4, 0, -1):
            kk = i / 4
            rr = max(1, int(hl_r * kk))
            alpha = int(50 * (1 - kk) + 20)
            blik = pygame.Surface((rr*2, rr*2), pygame.SRCALPHA)
            pygame.draw.circle(blik, (255, 255, 255, alpha), (rr, rr), rr)
            screen.blit(blik, (hl_x - rr, hl_y - rr),
                        special_flags=pygame.BLEND_ADD)

    def _draw_surface(self, surf, cx, cy, r):
        base, dark, light = self.colors
        if self.planet_type in ('rocky', 'mars'):
            for (lon, lat, size, tone) in self.spots:
                res = self._sphere_xy(lon, lat, r, cx, cy)
                if res is None: continue
                px, py, z3 = res
                if z3 < 0.12: continue
                cr = max(2, int(size * r * z3))
                pygame.draw.circle(surf, dark,
                                   (int(px + cr*0.35), int(py + cr*0.35)), cr)
                rim_col = tuple(min(255, int(c + 30)) for c in dark)
                pygame.draw.circle(surf, rim_col, (int(px), int(py)),
                                   max(1, cr - 1))
                floor_col = tuple(int(c * 0.7) for c in base)
                pygame.draw.circle(surf, floor_col, (int(px), int(py)),
                                   max(1, int(cr * 0.6)))
                pygame.draw.circle(surf, light,
                                   (int(px - cr*0.4), int(py - cr*0.4)),
                                   max(1, int(cr * 0.3)))
            if self.planet_type == 'mars':
                pygame.draw.ellipse(surf, (240, 245, 255),
                                    (cx - r*0.5, cy - r - 1, r*1.0, r*0.22))
                pygame.draw.ellipse(surf, (240, 245, 255),
                                    (cx - r*0.5, cy + r - r*0.20, r*1.0, r*0.22))
                pygame.draw.ellipse(surf, (200, 210, 230),
                                    (cx - r*0.3, cy - r + r*0.05,
                                     r*0.6, r*0.12))
            if self.kind == 'mercury':
                for (lon, lat, size, _) in self.spots[:5]:
                    res = self._sphere_xy(lon + 1.5, lat + 0.3, r, cx, cy)
                    if res is None: continue
                    px, py, z3 = res
                    if z3 < 0.2: continue
                    cr = max(2, int(size * r * z3 * 0.6))
                    pygame.draw.circle(surf, tuple(int(c*0.75) for c in dark),
                                       (int(px), int(py)), cr)
        elif self.planet_type == 'earth':
            for (lon, lat, size, tone) in self.spots:
                res = self._sphere_xy(lon, lat, r, cx, cy)
                if res is None: continue
                px, py, z3 = res
                if z3 < 0.10: continue
                cr = max(2, int(size * r * z3))
                col = self.spot_color
                light_k = 0.55 + 0.45 * z3
                cc = (int(col[0]*light_k), int(col[1]*light_k), int(col[2]*light_k))
                pygame.draw.circle(surf, cc, (int(px), int(py)), cr)
                pygame.draw.circle(surf, cc,
                                   (int(px + cr*0.5), int(py + cr*0.25)),
                                   max(1, int(cr * 0.7)))
                pygame.draw.circle(surf, cc,
                                   (int(px - cr*0.4), int(py + cr*0.3)),
                                   max(1, int(cr * 0.55)))
                if tone > 0.85:
                    desert = tuple(min(255, int(c*f)) for c, f in
                                    zip(col, (1.3, 1.05, 0.7)))
                    pygame.draw.circle(surf, desert,
                                       (int(px + cr*0.2), int(py - cr*0.2)),
                                       max(1, int(cr * 0.4)))
            pygame.draw.ellipse(surf, (235, 245, 255),
                                (cx - r*0.55, cy - r - 1, r*1.1, r*0.22))
            pygame.draw.ellipse(surf, (255, 255, 255),
                                (cx - r*0.4, cy - r + 2, r*0.8, r*0.14))
            pygame.draw.ellipse(surf, (235, 245, 255),
                                (cx - r*0.55, cy + r - r*0.20, r*1.1, r*0.22))
            pygame.draw.ellipse(surf, (255, 255, 255),
                                (cx - r*0.4, cy + r - r*0.15, r*0.8, r*0.14))
            for (lon, lat, size) in self.clouds:
                res = self._sphere_xy(lon + self.cloud_offset, lat, r, cx, cy)
                if res is None: continue
                px, py, z3 = res
                if z3 < 0.2: continue
                cr = max(2, int(size * r * z3))
                cloud = pygame.Surface((cr*3, cr*2), pygame.SRCALPHA)
                pygame.draw.ellipse(cloud, (255, 255, 255, 160),
                                    (0, 0, cr*3, cr*2))
                pygame.draw.ellipse(cloud, (200, 210, 230, 100),
                                    (0, cr//2, cr*3, cr))
                surf.blit(cloud, (int(px - cr*1.5), int(py - cr)))
        elif self.planet_type == 'cloudy':
            for (lon, lat, size) in self.clouds:
                res = self._sphere_xy(lon + self.cloud_offset*0.5, lat, r, cx, cy)
                if res is None: continue
                px, py, z3 = res
                if z3 < 0.15: continue
                cr = max(3, int(size * r * z3 * 1.3))
                cloud = pygame.Surface((cr*4, cr*2), pygame.SRCALPHA)
                pygame.draw.ellipse(cloud, (*light, 110), (0, 0, cr*4, cr*2))
                pygame.draw.ellipse(cloud, (255, 250, 220, 80),
                                    (cr//2, cr//4, cr*3, cr))
                surf.blit(cloud, (int(px - cr*2), int(py - cr)))
            haze = pygame.Surface((r*2 + 4, r*2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(haze, (255, 220, 150, 30), (cx, cy), r)
            surf.blit(haze, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
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
                pygame.draw.rect(surf, col,
                                 (cx - half_w, cy + y_off - band_h/2,
                                  half_w*2, band_h))
                edge_col = tuple(int(c * 0.7) for c in col)
                pygame.draw.line(surf, edge_col,
                                 (cx - half_w, cy + y_off - band_h/2),
                                 (cx + half_w, cy + y_off - band_h/2), 1)
            for storm in self.storms:
                lon = storm['lon'] + self.cloud_offset * 0.3
                lat = storm['lat']
                res = self._sphere_xy(lon, lat, r, cx, cy)
                if res is None: continue
                px, py, z3 = res
                if z3 < 0.15: continue
                cr = max(3, int(storm['size'] * r * z3))
                pygame.draw.ellipse(surf,
                    tuple(min(255, c+30) for c in storm['color']),
                    (int(px - cr*1.6), int(py - cr*0.7),
                     int(cr*3.2), int(cr*1.4)))
                pygame.draw.ellipse(surf, storm['color'],
                                    (int(px - cr*1.2), int(py - cr*0.55),
                                     int(cr*2.4), int(cr*1.1)))
                pygame.draw.ellipse(surf,
                    tuple(min(255, c+60) for c in storm['color']),
                    (int(px - cr*0.5), int(py - cr*0.25),
                     int(cr), int(cr*0.5)))
            if self.kind == 'jupiter':
                px = cx + r * 0.20; py = cy + r * 0.15
                pr = max(3, int(r * 0.16))
                for rr_scale in [1.8, 1.5, 1.3]:
                    pygame.draw.ellipse(surf, (230, 200, 170),
                        (int(px - pr*rr_scale), int(py - pr*rr_scale*0.5),
                         int(pr*2*rr_scale), int(pr*rr_scale)), 1)
                pygame.draw.ellipse(surf, self.spot_color,
                                    (int(px - pr*1.4), int(py - pr*0.7),
                                     pr*2, int(pr*1.4)))
                pygame.draw.ellipse(surf,
                                    tuple(max(0, c-30) for c in self.spot_color),
                                    (int(px - pr*1.4), int(py - pr*0.7),
                                     pr*2, int(pr*1.4)), 1)
                pygame.draw.ellipse(surf,
                                    tuple(min(255, c+40) for c in self.spot_color),
                                    (int(px - pr*0.6), int(py - pr*0.3),
                                     int(pr*1.2), int(pr*0.6)))
            if self.kind == 'neptune':
                px = cx - r * 0.15; py = cy + r * 0.10
                pr = max(3, int(r * 0.12))
                pygame.draw.ellipse(surf, self.spot_color,
                                    (int(px - pr*1.3), int(py - pr*0.6),
                                     pr*2, pr))
                rnd_n = random.Random(42)
                for _ in range(3):
                    rx = px + rnd_n.uniform(-pr, pr)
                    ry = py - pr*0.8
                    pygame.draw.ellipse(surf, (240, 245, 255),
                                        (int(rx - pr*0.4), int(ry - pr*0.15),
                                         int(pr*0.8), int(pr*0.3)))

    def _draw_ring(self, cx, cy, r, half):
        """BUGFIX: разделено на заднюю и переднюю половины."""
        ring_col1 = (230, 210, 160)
        ring_col2 = (200, 175, 120)
        ring_col3 = (170, 145, 95)
        ring_col4 = (240, 220, 180)
        if half == 'back':
            start, end = 0, math.pi
        else:
            start, end = math.pi, math.tau
        rect_back = pygame.Rect(cx - int(r*2.4), cy - int(r*0.44),
                                int(r*4.8), int(r*0.88))
        pygame.draw.arc(screen, ring_col3, rect_back, start, end, max(2, r//18))
        rect_mid = pygame.Rect(cx - int(r*2.15), cy - int(r*0.40),
                               int(r*4.3), int(r*0.80))
        pygame.draw.arc(screen, ring_col2, rect_mid, start, end, max(2, r//20))
        rect_in = pygame.Rect(cx - int(r*1.9), cy - int(r*0.35),
                              int(r*3.8), int(r*0.70))
        pygame.draw.arc(screen, ring_col1, rect_in, start, end, max(1, r//22))
        rect_bright = pygame.Rect(cx - int(r*1.7), cy - int(r*0.30),
                                  int(r*3.4), int(r*0.60))
        pygame.draw.arc(screen, ring_col4, rect_bright, start, end, max(1, r//26))

# ============================================================
#              ЧАСТИЦЫ / ЗВЁЗДЫ
# ============================================================
class Particle:
    def __init__(self,x,y,color=None):
        self.x,self.y=x,y
        a=random.uniform(0,math.tau); sp=random.uniform(100,450)
        self.vx=math.cos(a)*sp; self.vy=math.sin(a)*sp
        self.life=random.uniform(0.35,0.8); self.max=self.life
        self.color=color or random.choice([ORANGE,YELLOW,RED,WHITE,(255,200,100)])
        self.size=random.uniform(2,5)
    def update(self,dt):
        self.x+=self.vx*dt; self.y+=self.vy*dt
        self.vx*=0.93; self.vy*=0.93; self.life-=dt
    def draw(self,surf):
        k=max(0,self.life/self.max); r=max(1,int(self.size*k))
        g=get_glow(self.color,r*3)
        if g: surf.blit(g,(int(self.x)-r*3,int(self.y)-r*3),
                        special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surf,self.color,(int(self.x),int(self.y)),r)

class StarField:
    def __init__(self):
        self.stars=[]
        for _ in range(280):
            layer=random.choices([0,1,2],weights=[5,3,1])[0]
            if layer==0: sz=1; br=random.randint(80,140); sp=random.uniform(200,350)
            elif layer==1: sz=random.randint(1,2); br=random.randint(140,200); sp=random.uniform(350,600)
            else: sz=random.randint(2,3); br=random.randint(200,255); sp=random.uniform(600,900)
            self.stars.append({
                'v':V4(random.uniform(-3500,3500),random.uniform(-2500,2500),
                       random.uniform(100,4000),random.uniform(-200,200)),
                'b':br,'sz':sz,'sp':sp,
                'tw':random.uniform(0,math.tau),
                'tw_s':random.uniform(1.0,2.5),
                'hue':random.choice(['white','blue','warm']),
            })
    def update(self,dt):
        for s in self.stars:
            s['tw']+=s['tw_s']*dt
            s['v'].z-=s['sp']*dt
            if s['v'].z<50:
                s['v'].z=4000
                s['v'].x=random.uniform(-3500,3500)
                s['v'].y=random.uniform(-2500,2500)
    def draw(self,wr):
        for s in self.stars:
            v=s['v']
            for pl in ('XW','YW','ZW'):
                if abs(wr[pl])>1e-6:
                    v=rot4(v,wr[pl],pl)
            p=proj(v.x,v.y,v.z)
            if p is None: continue
            sx,sy,k,rz=p
            if sx<-15 or sx>W+15 or sy<-15 or sy>H+15: continue
            tw=0.7+0.3*math.sin(s['tw'])
            b=max(40,min(255,int(s['b']*tw)))
            if s['hue']=='blue': col=(int(b*0.7),int(b*0.85),b)
            elif s['hue']=='warm': col=(b,int(b*0.85),int(b*0.7))
            else: col=(b,b,min(255,b+30))
            col=w_color(col,v.w)
            size=s['sz']
            if size>=2:
                g=get_glow(col,size*4)
                if g: screen.blit(g,(int(sx)-size*4,int(sy)-size*4),
                                  special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(screen,col,(int(sx),int(sy)),size)

# ============================================================
#              КНОПКА
# ============================================================
class Button:
    def __init__(self,x,y,w,h,text,color):
        self.rect=pygame.Rect(x,y,w,h); self.text=text; self.color=color
        self.hover=False; self.font=pygame.font.Font(None,30)
    def handle(self,ev):
        if ev.type==pygame.MOUSEMOTION: self.hover=self.rect.collidepoint(ev.pos)
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            if self.rect.collidepoint(ev.pos): return True
        return False
    def draw(self,surf):
        col=self.color
        if self.hover: col=tuple(min(255,v+50) for v in col)
        s=pygame.Surface((self.rect.w,self.rect.h),pygame.SRCALPHA)
        for y in range(self.rect.h):
            t=y/max(1,self.rect.h-1)
            c=(int(col[0]*(1-t*0.6)),int(col[1]*(1-t*0.6)),int(col[2]*(1-t*0.6)))
            pygame.draw.line(s,c,(0,y),(self.rect.w,y))
        mask=pygame.Surface((self.rect.w,self.rect.h),pygame.SRCALPHA)
        pygame.draw.rect(mask,(255,255,255,255),(0,0,self.rect.w,self.rect.h),
                         border_radius=8)
        s.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.rect(s,(200,220,255,200),(0,0,self.rect.w,self.rect.h),2,
                         border_radius=8)
        surf.blit(s,self.rect.topleft)
        img=self.font.render(self.text,True,WHITE)
        surf.blit(img,img.get_rect(center=self.rect.center))

# ============================================================
#              ИГРА
# ============================================================
class Game:
    def __init__(self):
        self.state="menu"; self.ship=Ship()
        self.asteroids=[]; self.particles=[]
        self.world_rot={'XW':0.0,'YW':0.0,'ZW':0.0}
        self.starfield=StarField()
        self.planets=[SolarPlanet() for _ in range(5)]
        self.spawn_t=0.0; self.elapsed=0.0; self.best=0.0
        self.dash_cd=0.0; self.dash_t=0.0; self.dash_v=(0.0,0.0)
        self.pulse_cd=0.0; self.flash=0.0
        self.f_xs=pygame.font.Font(None,20); self.f_s=pygame.font.Font(None,24)
        self.f_m=pygame.font.Font(None,32); self.f_l=pygame.font.Font(None,48)
        self.f_big=pygame.font.Font(None,76)
        cx,cy=W//2,H//2; bw,bh=280,52
        self.btn_play=Button(cx-bw//2,cy-40,bw,bh,"ЗАПУСК",(50,130,90))
        self.btn_quit=Button(cx-bw//2,cy+40,bw,bh,"ВЫХОД",(140,50,60))
        self.btn_resume=Button(cx-bw//2,cy-80,bw,bh,"ПРОДОЛЖИТЬ",(50,130,90))
        self.btn_menu=Button(cx-bw//2,cy,bw,bh,"В МЕНЮ",(60,100,180))
        self.btn_quit2=Button(cx-bw//2,cy+80,bw,bh,"ВЫХОД",(140,50,60))
        self.btn_retry=Button(cx-bw//2,cy+60,bw,bh,"ЕЩЁ РАЗ",(50,130,90))
        self.btn_menu2=Button(cx-bw//2,cy+120,bw,bh,"В МЕНЮ",(60,100,180))
        self.reset()

    def reset(self):
        self.ship=Ship(); self.asteroids.clear(); self.particles.clear()
        self.world_rot={'XW':0.0,'YW':0.0,'ZW':0.0}
        self.spawn_t=0.0; self.elapsed=0.0
        self.dash_cd=0.0; self.dash_t=0.0; self.pulse_cd=0.0; self.flash=0.0
        for _ in range(5): self.spawn_asteroid()

    def spawn_asteroid(self):
        r = random.random()
        if r < 0.35:
            mode = 'homing'
            tx = self.ship.x; ty = self.ship.y
        elif r < 0.75:
            mode = 'aimed'
            tx = self.ship.x + random.uniform(-90, 90)
            ty = self.ship.y + random.uniform(-90, 90)
        else:
            mode = 'sweep'
            tx = random.uniform(-520, 520)
            ty = random.uniform(-370, 370)
        side = random.choice(['front','front','left','right','top','top'])
        if side == 'front':
            x = random.uniform(-800, 800); y = random.uniform(-600, 600)
            z = random.uniform(2400, 3200)
        elif side == 'left':
            x = random.uniform(-1600, -900); y = random.uniform(-700, 700)
            z = random.uniform(1200, 2600)
        elif side == 'right':
            x = random.uniform(900, 1600); y = random.uniform(-700, 700)
            z = random.uniform(1200, 2600)
        else:
            x = random.uniform(-900, 900); y = random.uniform(-1400, -800)
            z = random.uniform(1200, 2600)
        dx = tx - x; dy = ty - y; dz = -z
        d = math.sqrt(dx*dx + dy*dy + dz*dz) or 1.0
        speed = random.uniform(280, 420)
        vx = dx / d * speed; vy = dy / d * speed; vz = dz / d * speed
        w = random.uniform(-180, 180); vw = random.uniform(-40, 40)
        ast = Asteroid(V4(x, y, z, w), random.randint(0, 999999),
                       vel_hint=V4(vx, vy, vz, vw))
        ast.homing = (mode == 'homing')
        self.asteroids.append(ast)

    def start_dash(self):
        if self.dash_cd>0 or self.dash_t>0: return
        keys=pygame.key.get_pressed()
        dx=dy=0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx-=1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx+=1
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy-=1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy+=1
        if dx==0 and dy==0: dy=-1
        n=math.hypot(dx,dy)
        self.dash_v=(dx/n*2400,dy/n*2400); self.dash_t=0.18
        self.dash_cd=1.2; self.ship.invuln=max(self.ship.invuln,0.4)

    def pulse(self):
        if self.pulse_cd>0: return
        self.pulse_cd=1.2; self.flash=0.35
        for a in self.asteroids:
            wp=a.get_world_pos(self.world_rot)
            if abs(wp.w)<SLICE_W*1.5:
                d=1 if wp.w>=0 else -1
                a.vel.w+=d*500

    def handle(self,ev):
        if ev.type==pygame.QUIT: return "quit"
        if self.state=="menu":
            if self.btn_play.handle(ev):
                self.reset(); self.state="playing"; return
            if self.btn_quit.handle(ev): return "quit"
        elif self.state=="paused":
            if self.btn_resume.handle(ev): self.state="playing"; return
            if self.btn_menu.handle(ev): self.state="menu"; return
            if self.btn_quit2.handle(ev): return "quit"
        elif self.state=="game_over":
            if self.btn_retry.handle(ev):
                self.reset(); self.state="playing"; return
            if self.btn_menu2.handle(ev): self.state="menu"; return
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE:
                if self.state=="playing": self.state="paused"
                elif self.state=="paused": self.state="playing"
                else: return "quit"
            if self.state=="playing":
                if ev.key in (pygame.K_LSHIFT,pygame.K_RSHIFT): self.start_dash()
                if ev.key==pygame.K_SPACE: self.pulse()
            if self.state=="game_over" and ev.key==pygame.K_SPACE:
                self.reset(); self.state="playing"
        return None

    def update(self,dt):
        if self.flash>0: self.flash-=dt*2.5
        if self.pulse_cd>0: self.pulse_cd-=dt
        self.starfield.update(dt)
        for p in self.planets: p.update(dt)
        if self.state!="playing": return
        keys=pygame.key.get_pressed()
        self.ship.update(keys,dt)
        if self.dash_t>0:
            self.dash_t-=dt
            self.ship.x+=self.dash_v[0]*dt
            self.ship.y+=self.dash_v[1]*dt
            self.ship.x=max(-SHIP_LIMIT_X,min(SHIP_LIMIT_X,self.ship.x))
            self.ship.y=max(-SHIP_LIMIT_Y,min(SHIP_LIMIT_Y,self.ship.y))
        if self.dash_cd>0: self.dash_cd-=dt
        sp=0.9
        if keys[pygame.K_q]: self.world_rot['XW']+=sp*dt
        if keys[pygame.K_e]: self.world_rot['XW']-=sp*dt
        if keys[pygame.K_r]: self.world_rot['YW']+=sp*dt
        if keys[pygame.K_f]: self.world_rot['YW']-=sp*dt
        if keys[pygame.K_t]: self.world_rot['ZW']+=sp*dt
        if keys[pygame.K_g]: self.world_rot['ZW']-=sp*dt
        self.spawn_t+=dt
        interval=max(0.4,1.0-self.elapsed*0.008)
        if self.spawn_t>=interval and len(self.asteroids)<40:
            self.spawn_t=0; self.spawn_asteroid()
        for a in self.asteroids: a.update(dt,self.ship)
        for p in self.particles: p.update(dt)
        if self.ship.invuln<=0:
            for a in self.asteroids:
                if not a.alive: continue
                wp=a.get_world_pos(self.world_rot)
                if abs(wp.w)<SLICE_W:
                    dx=wp.x-self.ship.x; dy=wp.y-self.ship.y
                    r_hit = a.radius + 22
                    if (abs(dx)<r_hit and abs(dy)<r_hit
                            and -180 < wp.z < 180):
                        self.ship.lives-=1; self.ship.invuln=1.5
                        a.hp-=1; a.hit_flash=0.3
                        if a.hp<=0: a.alive=False
                        sp_scr=proj(self.ship.x,self.ship.y,0)
                        if sp_scr:
                            for _ in range(45):
                                self.particles.append(Particle(sp_scr[0],sp_scr[1]))
                        if self.ship.lives<=0:
                            self.best=max(self.best,self.elapsed)
                            self.state="game_over"
                        break
        self.asteroids=[a for a in self.asteroids if a.alive]
        self.particles=[p for p in self.particles if p.life>0]
        self.elapsed+=dt

    def draw_world(self):
        screen.fill(BLACK)
        for p in self.planets: p.draw()
        self.starfield.draw(self.world_rot)
        # BUGFIX: расширен диапазон видимости — рисуем всё, что не за камерой
        vis=[]
        for a in self.asteroids:
            wp=a.get_world_pos(self.world_rot)
            if wp.z > -400:  # было: wp.z > 50
                vis.append((wp.z, a))
        vis.sort(key=lambda x: -x[0])
        for (_,a) in vis: a.draw(self.world_rot)
        self.ship.draw()
        for p in self.particles: p.draw(screen)

    def panel(self,r,alpha=200):
        s=pygame.Surface((r.w,r.h),pygame.SRCALPHA)
        pygame.draw.rect(s,(*PANEL,alpha),(0,0,r.w,r.h),border_radius=10)
        screen.blit(s,r.topleft)
        pygame.draw.rect(screen,BORDER,r,1,border_radius=10)

    def txt(self,text,font,color,x,y,center=False):
        img=font.render(text,True,color); sh=font.render(text,True,(0,0,0))
        if center:
            screen.blit(sh,sh.get_rect(center=(x+1,y+1)))
            screen.blit(img,img.get_rect(center=(x,y)))
        else:
            screen.blit(sh,sh.get_rect(topleft=(x+1,y+1)))
            screen.blit(img,img.get_rect(topleft=(x,y)))

    def draw_hud(self):
        r=pygame.Rect(15,15,200,82); self.panel(r)
        self.txt("ВРЕМЯ",self.f_xs,GREY,30,22)
        self.txt(f"{int(self.elapsed)} сек",self.f_m,WHITE,30,42)
        self.txt(f"рекорд {int(self.best)}",self.f_xs,CYAN,30,78)
        r2=pygame.Rect(W//2-85,15,170,62); self.panel(r2)
        spd=1.0+self.elapsed*0.025
        col=YELLOW if spd<2 else (ORANGE if spd<3 else RED)
        self.txt(f"x{spd:.2f}",self.f_m,col,W//2,32,True)
        self.txt("ТЕМП",self.f_xs,GREY,W//2,60,True)
        r3=pygame.Rect(W-180,15,165,62); self.panel(r3)
        self.txt("ЖИЗНИ",self.f_xs,GREY,W-165,22)
        for i in range(3):
            cx=W-145+i*32; cy=55
            if i<self.ship.lives:
                g=get_glow(RED,14)
                if g: screen.blit(g,(cx-14,cy-14),special_flags=pygame.BLEND_ADD)
                pygame.draw.circle(screen,RED,(cx,cy),8)
                pygame.draw.circle(screen,(255,220,220),(cx,cy),8,2)
            else:
                pygame.draw.circle(screen,(40,40,55),(cx,cy),8)
                pygame.draw.circle(screen,(80,85,105),(cx,cy),8,1)
        sp=math.hypot(self.ship.vx,self.ship.vy)
        r_sp=pygame.Rect(W//2-85,80,170,30); self.panel(r_sp)
        sp_k=min(1.0,sp/self.ship.max_sp)
        bar=pygame.Rect(W//2-75,88,150,12)
        pygame.draw.rect(screen,(20,30,50),bar,border_radius=6)
        col_sp=GREEN if sp_k<0.5 else (YELLOW if sp_k<0.85 else RED)
        pygame.draw.rect(screen,col_sp,(bar.x,bar.y,int(bar.w*sp_k),bar.h),
                         border_radius=6)
        pygame.draw.rect(screen,BORDER,bar,1,border_radius=6)
        self.txt(f"{int(sp)}",self.f_xs,WHITE,W//2,105,True)
        r4=pygame.Rect(15,H-90,200,75); self.panel(r4)
        self.txt("РЫВОК [SHIFT]",self.f_xs,GREY,30,H-84)
        bar=pygame.Rect(30,H-68,170,8)
        pygame.draw.rect(screen,(20,30,50),bar,border_radius=4)
        k=1-self.dash_cd/1.2 if self.dash_cd>0 else 1
        k=max(0,min(1,k))
        if k>0:
            c=GREEN if k>=1 else (YELLOW if k>0.4 else RED)
            pygame.draw.rect(screen,c,(bar.x,bar.y,int(bar.w*k),bar.h),
                             border_radius=4)
        pygame.draw.rect(screen,BORDER,bar,1,border_radius=4)
        self.txt("ИМПУЛЬС [SPACE]",self.f_xs,GREY,30,H-48)
        bar2=pygame.Rect(30,H-32,170,8)
        pygame.draw.rect(screen,(20,30,50),bar2,border_radius=4)
        k2=1-self.pulse_cd/1.2 if self.pulse_cd>0 else 1
        k2=max(0,min(1,k2))
        if k2>0:
            c=CYAN if k2>=1 else (YELLOW if k2>0.4 else RED)
            pygame.draw.rect(screen,c,(bar2.x,bar2.y,int(bar2.w*k2),bar2.h),
                             border_radius=4)
        pygame.draw.rect(screen,BORDER,bar2,1,border_radius=4)
        r5=pygame.Rect(W-215,H-105,200,90); self.panel(r5)
        self.txt("4D ВРАЩЕНИЕ",self.f_xs,GREY,W-200,H-100)
        for i,(key,name,pl) in enumerate([("Q/E","XW",'XW'),
                                            ("R/F","YW",'YW'),
                                            ("T/G","ZW",'ZW')]):
            y=H-78+i*20
            self.txt(key,self.f_xs,CYAN,W-200,y)
            self.txt(name,self.f_xs,DIM,W-160,y)
            a=self.world_rot[pl]; v=(math.sin(a)+1)*0.5
            bx=W-125; bw=100
            pygame.draw.rect(screen,(15,25,45),(bx,y+2,bw,8),border_radius=4)
            pygame.draw.rect(screen,CYAN,(bx,y+2,int(bw*v),8),border_radius=4)
            pygame.draw.rect(screen,BORDER,(bx,y+2,bw,8),1,border_radius=4)
        self.txt("WASD · SPACE импульс · SHIFT рывок · "
                 "Q/E R/F T/G 4D · ESC пауза",
                 self.f_xs,GREY,W//2,H-18,True)

    def draw_menu(self):
        screen.fill(BLACK)
        for p in self.planets: p.draw()
        self.starfield.draw(self.world_rot)
        old_x, old_y = self.ship.x, self.ship.y
        self.ship.x = 0; self.ship.y = -80
        self.ship.draw()
        self.ship.x, self.ship.y = old_x, old_y
        ov=pygame.Surface((W,H),pygame.SRCALPHA)
        ov.fill((0,0,15,140)); screen.blit(ov,(0,0))
        self.txt("4D HYPERFLIGHT",self.f_big,CYAN,W//2,140,True)
        self.txt("объёмный корабль · металл и бронза · планеты СС",
                 self.f_s,GREY,W//2,190,True)
        self.btn_play.draw(screen); self.btn_quit.draw(screen)
        if self.best>0:
            self.txt(f"РЕКОРД  {int(self.best)} сек",self.f_m,YELLOW,
                     W//2,H-50,True)

    def draw_pause(self):
        self.draw_world(); self.draw_hud()
        ov=pygame.Surface((W,H),pygame.SRCALPHA)
        ov.fill((0,0,15,180)); screen.blit(ov,(0,0))
        self.txt("ПАУЗА",self.f_big,YELLOW,W//2,H//2-150,True)
        self.btn_resume.draw(screen); self.btn_menu.draw(screen)
        self.btn_quit2.draw(screen)

    def draw_game_over(self):
        self.draw_world()
        ov=pygame.Surface((W,H),pygame.SRCALPHA)
        ov.fill((30,0,0,200)); screen.blit(ov,(0,0))
        self.txt("СРЕЗ ПОТЕРЯН",self.f_big,RED,W//2,H//2-160,True)
        r=pygame.Rect(W//2-200,H//2-100,400,120); self.panel(r,alpha=220)
        self.txt("ВРЕМЯ В 4D",self.f_xs,GREY,W//2,H//2-75,True)
        self.txt(f"{int(self.elapsed)} сек",self.f_l,WHITE,W//2,H//2-35,True)
        if int(self.elapsed)>=int(self.best):
            self.txt("★ НОВЫЙ РЕКОРД ★",self.f_s,YELLOW,W//2,H//2+15,True)
        else:
            self.txt(f"Рекорд: {int(self.best)} сек",self.f_s,CYAN,
                     W//2,H//2+15,True)
        self.btn_retry.draw(screen); self.btn_menu2.draw(screen)

    def draw(self):
        if self.state=="menu": self.draw_menu()
        elif self.state=="playing": self.draw_world(); self.draw_hud()
        elif self.state=="paused": self.draw_pause()
        elif self.state=="game_over": self.draw_game_over()
        if self.flash>0:
            ov=pygame.Surface((W,H),pygame.SRCALPHA)
            ov.fill((0,220,255,int(70*self.flash)))
            screen.blit(ov,(0,0),special_flags=pygame.BLEND_ADD)

# ============================================================
def main():
    g=Game(); running=True; dt=0.0
    while running:
        for ev in pygame.event.get():
            if g.handle(ev)=="quit": running=False
        g.update(dt); g.draw()
        pygame.display.flip()
        dt=min(clock.tick(FPS)/1000.0,0.05)
    pygame.quit()

if __name__=="__main__":
    main()