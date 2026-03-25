-- CreatureData.lua
-- All sea creature enemies with stats and spawn zones
-- Place in ReplicatedStorage/Modules as a ModuleScript

local CreatureData = {}

CreatureData.Creatures = {

	-- ── ZONE 1 ─────────────────────────────────────────────────
	Crab = {
		id          = "Crab",
		displayName = "Giant Crab",
		zone        = 1,
		health      = 60,
		damage      = 10,
		speed       = 8,
		reward      = { Coins = 5, Minerals = 2 },
		attackRange = 6,
		color       = Color3.fromRGB(220, 80, 20),
		size        = Vector3.new(4, 2, 4),
		spawnWeight = 60,  -- higher = more common
	},

	Jellyfish = {
		id          = "Jellyfish",
		displayName = "Electric Jellyfish",
		zone        = 1,
		health      = 30,
		damage      = 15,
		speed       = 5,
		reward      = { Coins = 8, Power = 1 },
		attackRange = 10,
		color       = Color3.fromRGB(180, 100, 255),
		size        = Vector3.new(3, 4, 3),
		spawnWeight = 40,
	},

	-- ── ZONE 2 ─────────────────────────────────────────────────
	Shark = {
		id          = "Shark",
		displayName = "Bull Shark",
		zone        = 2,
		health      = 200,
		damage      = 35,
		speed       = 18,
		reward      = { Coins = 25, Minerals = 10 },
		attackRange = 8,
		color       = Color3.fromRGB(100, 120, 140),
		size        = Vector3.new(6, 3, 12),
		spawnWeight = 50,
	},

	Eel = {
		id          = "Eel",
		displayName = "Electric Eel",
		zone        = 2,
		health      = 120,
		damage      = 50,
		speed       = 14,
		reward      = { Coins = 30, Power = 5 },
		attackRange = 12,
		color       = Color3.fromRGB(80, 200, 100),
		size        = Vector3.new(2, 2, 14),
		spawnWeight = 30,
		specialAttack = "EMP",  -- disables turrets briefly
	},

	-- ── ZONE 3 ─────────────────────────────────────────────────
	AnglerFish = {
		id          = "AnglerFish",
		displayName = "Angler Fish",
		zone        = 3,
		health      = 500,
		damage      = 80,
		speed       = 10,
		reward      = { Coins = 100, Minerals = 40 },
		attackRange = 15,
		color       = Color3.fromRGB(30, 30, 80),
		size        = Vector3.new(8, 6, 10),
		spawnWeight = 40,
		bioluminescent = true,
	},

	GiantSquid = {
		id          = "GiantSquid",
		displayName = "Giant Squid",
		zone        = 3,
		health      = 800,
		damage      = 120,
		speed       = 12,
		reward      = { Coins = 200, Minerals = 80 },
		attackRange = 20,
		color       = Color3.fromRGB(150, 20, 80),
		size        = Vector3.new(10, 8, 20),
		spawnWeight = 20,
		specialAttack = "InkBlast",  -- blinds nearby turrets
	},

	-- ── ZONE 4 (ABYSS) ─────────────────────────────────────────
	Megalodon = {
		id          = "Megalodon",
		displayName = "Megalodon",
		zone        = 4,
		health      = 3000,
		damage      = 300,
		speed       = 20,
		reward      = { Coins = 1000, Minerals = 400 },
		attackRange = 25,
		color       = Color3.fromRGB(40, 40, 60),
		size        = Vector3.new(20, 10, 40),
		spawnWeight = 15,
		isBoss      = false,
	},

	-- ── BOSSES ─────────────────────────────────────────────────
	KrakenBoss = {
		id          = "KrakenBoss",
		displayName = "THE KRAKEN",
		zone        = 3,
		health      = 10000,
		damage      = 500,
		speed       = 8,
		reward      = { Coins = 5000, Minerals = 2000, Food = 500 },
		attackRange = 40,
		color       = Color3.fromRGB(100, 0, 50),
		size        = Vector3.new(30, 20, 30),
		spawnWeight = 0,  -- boss, spawned manually
		isBoss      = true,
		spawnInterval = 600,  -- 10 minutes
	},

	SeaTitanBoss = {
		id          = "SeaTitanBoss",
		displayName = "SEA TITAN",
		zone        = 4,
		health      = 50000,
		damage      = 2000,
		speed       = 6,
		reward      = { Coins = 25000, Minerals = 10000, Food = 2000 },
		attackRange = 60,
		color       = Color3.fromRGB(20, 0, 80),
		size        = Vector3.new(50, 40, 50),
		spawnWeight = 0,
		isBoss      = true,
		spawnInterval = 1800,  -- 30 minutes
	},
}

-- Helper: get creatures that spawn in a zone
function CreatureData.GetForZone(zoneLevel)
	local result = {}
	for _, creature in pairs(CreatureData.Creatures) do
		if creature.zone == zoneLevel and not creature.isBoss then
			table.insert(result, creature)
		end
	end
	return result
end

-- Helper: weighted random pick from a zone's creature pool
function CreatureData.PickRandom(zoneLevel)
	local pool = CreatureData.GetForZone(zoneLevel)
	local totalWeight = 0
	for _, c in ipairs(pool) do
		totalWeight = totalWeight + c.spawnWeight
	end
	local roll = math.random(1, totalWeight)
	local cumulative = 0
	for _, c in ipairs(pool) do
		cumulative = cumulative + c.spawnWeight
		if roll <= cumulative then
			return c
		end
	end
	return pool[1]
end

return CreatureData
