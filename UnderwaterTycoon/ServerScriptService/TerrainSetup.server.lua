-- TerrainSetup.server.lua
-- Procedurally generates the ocean floor, coral, rocks, and depth zones
-- Runs once on server start. Place in ServerScriptService as a Script.

local Workspace        = game:GetService("Workspace")
local TweenService     = game:GetService("TweenService")

local terrain = Workspace.Terrain

-- ── CONFIG ────────────────────────────────────────────────────────────────────

local WORLD_RADIUS   = 1500   -- studs radius of the ocean floor
local OCEAN_DEPTH    = 5000   -- how deep the map goes (Y = -5000 at bottom)
local WATER_LEVEL    = 0      -- Y = 0 is the ocean surface

-- Zone depth breakpoints (Y positions, negative = underwater)
local ZONE_DEPTHS = {
	{ name = "Sunlight",  yMin = -200,  yMax = 0     },
	{ name = "Twilight",  yMin = -1000, yMax = -200  },
	{ name = "Midnight",  yMin = -4000, yMax = -1000 },
	{ name = "Abyss",     yMin = -5000, yMax = -4000 },
}

-- ── FILL OCEAN WATER ─────────────────────────────────────────────────────────

terrain:FillBlock(
	CFrame.new(0, WATER_LEVEL - 2500, 0),
	Vector3.new(WORLD_RADIUS * 2, 5000, WORLD_RADIUS * 2),
	Enum.Material.Water
)

-- ── OCEAN FLOOR ───────────────────────────────────────────────────────────────

-- Flat sand base
terrain:FillBlock(
	CFrame.new(0, -210, 0),
	Vector3.new(WORLD_RADIUS * 2, 20, WORLD_RADIUS * 2),
	Enum.Material.Sand
)

-- Deeper rock layers
terrain:FillBlock(
	CFrame.new(0, -1020, 0),
	Vector3.new(WORLD_RADIUS * 2, 30, WORLD_RADIUS * 2),
	Enum.Material.Rock
)

terrain:FillBlock(
	CFrame.new(0, -4020, 0),
	Vector3.new(WORLD_RADIUS * 2, 40, WORLD_RADIUS * 2),
	Enum.Material.Basalt
)

terrain:FillBlock(
	CFrame.new(0, -5020, 0),
	Vector3.new(WORLD_RADIUS * 2, 50, WORLD_RADIUS * 2),
	Enum.Material.Basalt
)

-- ── SURFACE BOAT / SPAWN PLATFORM ─────────────────────────────────────────────

local boatFolder = Instance.new("Folder", Workspace)
boatFolder.Name  = "SurfacePlatform"

local function makePart(parent, name, size, pos, color, material, anchored)
	local p           = Instance.new("Part", parent)
	p.Name            = name
	p.Size            = size
	p.CFrame          = CFrame.new(pos)
	p.Color           = color
	p.Material        = material or Enum.Material.Wood
	p.Anchored        = anchored ~= false
	p.CanCollide      = true
	return p
end

-- Boat deck
makePart(boatFolder, "Deck",  Vector3.new(30, 2, 30),  Vector3.new(0, 2, 0),
	Color3.fromRGB(120, 80, 40), Enum.Material.Wood)

-- Railing posts
for _, corner in ipairs({ Vector3.new(14, 5, 14), Vector3.new(-14, 5, 14),
                           Vector3.new(14, 5, -14), Vector3.new(-14, 5, -14) }) do
	makePart(boatFolder, "Post", Vector3.new(1, 6, 1), corner,
		Color3.fromRGB(80, 50, 20), Enum.Material.Wood)
end

-- Dive hatch (decorative)
local hatch = makePart(boatFolder, "DiveHatch", Vector3.new(6, 0.5, 6), Vector3.new(0, 3.25, 0),
	Color3.fromRGB(60, 100, 160), Enum.Material.Metal)
hatch.CanCollide = false

-- Spawn point
local spawnPart = Instance.new("SpawnLocation", boatFolder)
spawnPart.Size  = Vector3.new(6, 1, 6)
spawnPart.CFrame = CFrame.new(0, 4, 0)
spawnPart.Color = Color3.fromRGB(100, 180, 255)
spawnPart.Anchored = true
spawnPart.Neutral  = true
spawnPart.Duration = 0

-- ── DECORATIVE CORAL & ROCKS (Zone 1) ────────────────────────────────────────

local decoFolder = Instance.new("Folder", Workspace)
decoFolder.Name  = "Decorations"

math.randomseed(os.time())

local CORAL_COLORS = {
	Color3.fromRGB(255, 80,  100),
	Color3.fromRGB(255, 160, 0),
	Color3.fromRGB(80,  220, 180),
	Color3.fromRGB(200, 80,  255),
}

-- Zone 1: coral reefs
for i = 1, 80 do
	local angle  = math.random() * math.pi * 2
	local radius = math.random(50, 400)
	local x      = math.cos(angle) * radius
	local z      = math.sin(angle) * radius
	local y      = -200 + math.random(0, 10)
	local height = math.random(4, 16)
	local width  = math.random(2, 6)

	local coral       = Instance.new("Part", decoFolder)
	coral.Name        = "Coral_" .. i
	coral.Anchored    = true
	coral.CanCollide  = true
	coral.Size        = Vector3.new(width, height, width)
	coral.CFrame      = CFrame.new(x, y + height / 2, z)
	coral.Color       = CORAL_COLORS[math.random(1, #CORAL_COLORS)]
	coral.Material    = Enum.Material.Neon
	coral.CastShadow  = false

	local mesh        = Instance.new("SpecialMesh", coral)
	mesh.MeshType     = Enum.MeshType.Torso
end

-- Zone 1-2: rocks
for i = 1, 60 do
	local angle  = math.random() * math.pi * 2
	local radius = math.random(40, 600)
	local depth  = math.random(50, 900)
	local x      = math.cos(angle) * radius
	local z      = math.sin(angle) * radius
	local y      = -depth
	local s      = math.random(4, 20)

	local rock       = Instance.new("Part", decoFolder)
	rock.Name        = "Rock_" .. i
	rock.Anchored    = true
	rock.CanCollide  = true
	rock.Size        = Vector3.new(s, s * 0.7, s)
	rock.CFrame      = CFrame.new(x, y, z) * CFrame.Angles(
		math.random() * 0.5, math.random() * math.pi * 2, math.random() * 0.5)
	rock.Color       = Color3.fromRGB(80 + math.random(0, 40), 80 + math.random(0, 30), 70 + math.random(0, 20))
	rock.Material    = Enum.Material.Rock
end

-- Zone 3: bioluminescent mushrooms / vents
for i = 1, 30 do
	local angle  = math.random() * math.pi * 2
	local radius = math.random(30, 500)
	local x      = math.cos(angle) * radius
	local z      = math.sin(angle) * radius
	local y      = -(1000 + math.random(0, 2800))

	local vent       = Instance.new("Part", decoFolder)
	vent.Name        = "Vent_" .. i
	vent.Anchored    = true
	vent.CanCollide  = true
	vent.Size        = Vector3.new(3, math.random(6, 20), 3)
	vent.CFrame      = CFrame.new(x, y, z)
	vent.Color       = Color3.fromRGB(255, 120, 0)
	vent.Material    = Enum.Material.Neon
	vent.CastShadow  = false

	-- Particle smoke effect (placeholder — attach ParticleEmitter in Studio)
	local att = Instance.new("Attachment", vent)
	att.Name  = "VentTop"
	att.Position = Vector3.new(0, vent.Size.Y / 2, 0)
end

-- Zone 4: volcanic floor cracks
for i = 1, 15 do
	local angle  = math.random() * math.pi * 2
	local radius = math.random(20, 400)
	local x      = math.cos(angle) * radius
	local z      = math.sin(angle) * radius
	local y      = -(4000 + math.random(0, 800))

	local crack      = Instance.new("Part", decoFolder)
	crack.Name       = "LavaCrack_" .. i
	crack.Anchored   = true
	crack.CanCollide = false
	crack.Size       = Vector3.new(math.random(5, 15), 1, math.random(3, 8))
	crack.CFrame     = CFrame.new(x, y, z)
	crack.Color      = Color3.fromRGB(255, 50, 0)
	crack.Material   = Enum.Material.Neon
	crack.CastShadow = false
end

print("[TerrainSetup] Ocean world generated.")
