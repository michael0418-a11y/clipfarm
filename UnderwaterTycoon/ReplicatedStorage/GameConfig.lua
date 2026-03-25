-- GameConfig.lua
-- Central configuration for Underwater Tycoon
-- Place in ReplicatedStorage as a ModuleScript

local GameConfig = {}

-- ============================================================
-- ZONES
-- ============================================================
GameConfig.Zones = {
	{
		name = "Sunlight Zone",
		minDepth = 0,
		maxDepth = 200,
		color = Color3.fromRGB(0, 150, 255),
		fogEnd = 300,
		ambientLight = Color3.fromRGB(100, 180, 255),
		unlockCost = 0,
		pressureLevel = 0,
	},
	{
		name = "Twilight Zone",
		minDepth = 200,
		maxDepth = 1000,
		color = Color3.fromRGB(30, 60, 150),
		fogEnd = 150,
		ambientLight = Color3.fromRGB(30, 60, 120),
		unlockCost = 500,
		pressureLevel = 1,
	},
	{
		name = "Midnight Zone",
		minDepth = 1000,
		maxDepth = 4000,
		color = Color3.fromRGB(10, 10, 60),
		fogEnd = 80,
		ambientLight = Color3.fromRGB(10, 20, 50),
		unlockCost = 5000,
		pressureLevel = 2,
	},
	{
		name = "The Abyss",
		minDepth = 4000,
		maxDepth = 10000,
		color = Color3.fromRGB(5, 0, 20),
		fogEnd = 40,
		ambientLight = Color3.fromRGB(5, 0, 20),
		unlockCost = 50000,
		pressureLevel = 3,
	},
}

-- ============================================================
-- RESOURCES
-- ============================================================
GameConfig.Resources = {
	Minerals = { icon = "⛏️", color = Color3.fromRGB(180, 130, 80) },
	Oxygen   = { icon = "💨", color = Color3.fromRGB(150, 220, 255) },
	Food     = { icon = "🐟", color = Color3.fromRGB(255, 200, 50) },
	Power    = { icon = "⚡", color = Color3.fromRGB(255, 230, 0) },
	Coins    = { icon = "💰", color = Color3.fromRGB(255, 215, 0) },
}

-- ============================================================
-- PLAYER DEFAULTS
-- ============================================================
GameConfig.PlayerDefaults = {
	Minerals = 100,
	Oxygen   = 200,
	Food     = 50,
	Power    = 50,
	Coins    = 0,
	MaxOxygen = 200,
	UnlockedZones = { 1 },  -- starts with Sunlight Zone
}

-- ============================================================
-- GAMEPLAY SETTINGS
-- ============================================================
GameConfig.Settings = {
	OxygenTickRate      = 1,    -- seconds between oxygen drain ticks
	OxygenDrainPerTick  = 1,    -- oxygen lost per tick while diving
	ResourceTickRate    = 5,    -- seconds between AFK resource generation
	PressureDamageRate  = 10,   -- seconds between pressure damage ticks (no shield)
	PressureDamageAmt   = 10,   -- HP damage per tick without proper shield
	CreatureSpawnRate   = 30,   -- seconds between creature wave spawns
	MaxModulesPerPlayer = 50,
	DataSaveInterval    = 60,   -- seconds between auto-saves
}

-- ============================================================
-- DIVING
-- ============================================================
GameConfig.Diving = {
	SwimSpeed       = 20,
	DescentSpeed    = 15,
	AscentSpeed     = 25,
	SurfaceDepth    = 5,        -- studs above water = "on surface"
}

return GameConfig
