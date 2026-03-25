-- ModuleData.lua
-- All buildable base modules with stats and costs
-- Place in ReplicatedStorage/Modules as a ModuleScript

local ModuleData = {}

ModuleData.Modules = {

	-- ── STARTER ────────────────────────────────────────────────
	StarterPod = {
		id           = "StarterPod",
		displayName  = "Starter Pod",
		description  = "Your first underwater home. Provides basic shelter.",
		category     = "Core",
		size         = Vector3.new(8, 8, 8),
		color        = Color3.fromRGB(180, 220, 255),
		cost         = { Coins = 0 },
		maxLevel     = 5,
		levelBonuses = {
			[1] = { OxygenStorage = 200 },
			[2] = { OxygenStorage = 400 },
			[3] = { OxygenStorage = 700 },
			[4] = { OxygenStorage = 1100 },
			[5] = { OxygenStorage = 1600 },
		},
		upgradeCost  = {
			[2] = { Minerals = 50,  Coins = 100 },
			[3] = { Minerals = 150, Coins = 300 },
			[4] = { Minerals = 400, Coins = 800 },
			[5] = { Minerals = 900, Coins = 2000 },
		},
		requiredZone = 1,
	},

	-- ── OXYGEN ─────────────────────────────────────────────────
	AirPump = {
		id           = "AirPump",
		displayName  = "Air Pump",
		description  = "Produces oxygen passively. Essential for survival.",
		category     = "Life Support",
		size         = Vector3.new(4, 6, 4),
		color        = Color3.fromRGB(100, 200, 255),
		cost         = { Minerals = 30, Coins = 50 },
		maxLevel     = 5,
		production   = { resource = "Oxygen", perTick = 5 },
		levelBonuses = {
			[1] = { OxygenPerTick = 5 },
			[2] = { OxygenPerTick = 12 },
			[3] = { OxygenPerTick = 22 },
			[4] = { OxygenPerTick = 36 },
			[5] = { OxygenPerTick = 55 },
		},
		upgradeCost = {
			[2] = { Minerals = 80,  Coins = 150 },
			[3] = { Minerals = 200, Coins = 400 },
			[4] = { Minerals = 500, Coins = 1000 },
			[5] = { Minerals = 1200, Coins = 2500 },
		},
		requiredZone = 1,
	},

	-- ── MINING ─────────────────────────────────────────────────
	Drill = {
		id           = "Drill",
		displayName  = "Mining Drill",
		description  = "Passively mines minerals from the ocean floor.",
		category     = "Production",
		size         = Vector3.new(4, 8, 4),
		color        = Color3.fromRGB(200, 160, 80),
		cost         = { Minerals = 20, Coins = 75 },
		maxLevel     = 5,
		production   = { resource = "Minerals", perTick = 3 },
		levelBonuses = {
			[1] = { MineralsPerTick = 3 },
			[2] = { MineralsPerTick = 7 },
			[3] = { MineralsPerTick = 14 },
			[4] = { MineralsPerTick = 25 },
			[5] = { MineralsPerTick = 40 },
		},
		upgradeCost = {
			[2] = { Minerals = 60,  Coins = 120 },
			[3] = { Minerals = 160, Coins = 350 },
			[4] = { Minerals = 420, Coins = 900 },
			[5] = { Minerals = 1000, Coins = 2200 },
		},
		requiredZone = 1,
	},

	-- ── FOOD ───────────────────────────────────────────────────
	FishTrap = {
		id           = "FishTrap",
		displayName  = "Fish Trap",
		description  = "Catches fish passively. Sells for Coins.",
		category     = "Production",
		size         = Vector3.new(5, 4, 5),
		color        = Color3.fromRGB(100, 200, 120),
		cost         = { Minerals = 40, Coins = 100 },
		maxLevel     = 5,
		production   = { resource = "Food", perTick = 2 },
		levelBonuses = {
			[1] = { FoodPerTick = 2 },
			[2] = { FoodPerTick = 5 },
			[3] = { FoodPerTick = 9 },
			[4] = { FoodPerTick = 15 },
			[5] = { FoodPerTick = 24 },
		},
		upgradeCost = {
			[2] = { Minerals = 100, Coins = 200 },
			[3] = { Minerals = 250, Coins = 500 },
			[4] = { Minerals = 600, Coins = 1200 },
			[5] = { Minerals = 1400, Coins = 3000 },
		},
		requiredZone = 1,
	},

	-- ── POWER ──────────────────────────────────────────────────
	SolarPanel = {
		id           = "SolarPanel",
		displayName  = "Solar Panel",
		description  = "Generates power near the surface. Zone 1 only.",
		category     = "Power",
		size         = Vector3.new(8, 1, 8),
		color        = Color3.fromRGB(50, 50, 200),
		cost         = { Minerals = 50, Coins = 120 },
		maxLevel     = 3,
		production   = { resource = "Power", perTick = 4 },
		levelBonuses = {
			[1] = { PowerPerTick = 4 },
			[2] = { PowerPerTick = 9 },
			[3] = { PowerPerTick = 16 },
		},
		upgradeCost = {
			[2] = { Minerals = 120, Coins = 250 },
			[3] = { Minerals = 350, Coins = 700 },
		},
		requiredZone = 1,
		maxZone = 1,  -- only works in sunlight zone
	},

	ThermalVent = {
		id           = "ThermalVent",
		displayName  = "Thermal Tap",
		description  = "Harnesses deep-sea vent energy. Requires Zone 3+.",
		category     = "Power",
		size         = Vector3.new(6, 6, 6),
		color        = Color3.fromRGB(255, 80, 20),
		cost         = { Minerals = 500, Coins = 1000 },
		maxLevel     = 5,
		production   = { resource = "Power", perTick = 15 },
		levelBonuses = {
			[1] = { PowerPerTick = 15 },
			[2] = { PowerPerTick = 30 },
			[3] = { PowerPerTick = 50 },
			[4] = { PowerPerTick = 75 },
			[5] = { PowerPerTick = 110 },
		},
		upgradeCost = {
			[2] = { Minerals = 800,  Coins = 1800 },
			[3] = { Minerals = 2000, Coins = 5000 },
			[4] = { Minerals = 5000, Coins = 12000 },
			[5] = { Minerals = 12000, Coins = 30000 },
		},
		requiredZone = 3,
	},

	-- ── DEFENSE ────────────────────────────────────────────────
	Turret = {
		id           = "Turret",
		displayName  = "Defense Turret",
		description  = "Auto-shoots sea creatures that approach your base.",
		category     = "Defense",
		size         = Vector3.new(4, 5, 4),
		color        = Color3.fromRGB(200, 50, 50),
		cost         = { Minerals = 100, Coins = 200, Power = 20 },
		maxLevel     = 5,
		stats        = { damage = 20, range = 50, fireRate = 1.5 },
		levelBonuses = {
			[1] = { damage = 20,  range = 50,  fireRate = 1.5 },
			[2] = { damage = 40,  range = 65,  fireRate = 1.2 },
			[3] = { damage = 70,  range = 80,  fireRate = 1.0 },
			[4] = { damage = 110, range = 100, fireRate = 0.8 },
			[5] = { damage = 160, range = 120, fireRate = 0.6 },
		},
		upgradeCost = {
			[2] = { Minerals = 200, Coins = 400 },
			[3] = { Minerals = 500, Coins = 1000 },
			[4] = { Minerals = 1200, Coins = 2500 },
			[5] = { Minerals = 3000, Coins = 6000 },
		},
		requiredZone = 1,
	},

	-- ── RESEARCH ───────────────────────────────────────────────
	ResearchLab = {
		id           = "ResearchLab",
		displayName  = "Research Lab",
		description  = "Unlocks upgrades and new module types over time.",
		category     = "Research",
		size         = Vector3.new(8, 6, 8),
		color        = Color3.fromRGB(180, 100, 255),
		cost         = { Minerals = 200, Coins = 500 },
		maxLevel     = 3,
		production   = { resource = "ResearchPoints", perTick = 1 },
		levelBonuses = {
			[1] = { ResearchPerTick = 1 },
			[2] = { ResearchPerTick = 3 },
			[3] = { ResearchPerTick = 6 },
		},
		upgradeCost = {
			[2] = { Minerals = 500, Coins = 1200 },
			[3] = { Minerals = 1500, Coins = 4000 },
		},
		requiredZone = 1,
	},

	-- ── PRESSURE SHIELD ────────────────────────────────────────
	PressureShield = {
		id           = "PressureShield",
		displayName  = "Pressure Shield",
		description  = "Required to survive deep zone pressure. Covers nearby modules.",
		category     = "Core",
		size         = Vector3.new(6, 6, 6),
		color        = Color3.fromRGB(0, 220, 200),
		cost         = { Minerals = 300, Coins = 700 },
		maxLevel     = 3,
		stats        = { radius = 30, pressureResist = 1 },
		levelBonuses = {
			[1] = { radius = 30, pressureResist = 1 },
			[2] = { radius = 50, pressureResist = 2 },
			[3] = { radius = 80, pressureResist = 3 },
		},
		upgradeCost = {
			[2] = { Minerals = 700,  Coins = 1500 },
			[3] = { Minerals = 2000, Coins = 5000 },
		},
		requiredZone = 2,
	},
}

-- Helper: get module by id
function ModuleData.Get(id)
	return ModuleData.Modules[id]
end

-- Helper: get all modules for a given zone level
function ModuleData.GetForZone(zoneLevel)
	local result = {}
	for _, mod in pairs(ModuleData.Modules) do
		if mod.requiredZone <= zoneLevel then
			if not mod.maxZone or zoneLevel <= mod.maxZone then
				table.insert(result, mod)
			end
		end
	end
	return result
end

return ModuleData
