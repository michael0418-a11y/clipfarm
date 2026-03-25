-- ResearchData.lua
-- Research tree: unlockable upgrades bought with ResearchPoints
-- Place in ReplicatedStorage/Modules as a ModuleScript

local ResearchData = {}

ResearchData.Tree = {

	-- ── PRODUCTION BRANCH ────────────────────────────────────────────────────

	FasterDrills = {
		id          = "FasterDrills",
		displayName = "Faster Drills",
		description = "Drills produce +50% more minerals per tick.",
		cost        = 20,
		requires    = {},
		effect      = { type = "ProductionBoost", module = "Drill", multiplier = 1.5 },
		icon        = "⛏️",
	},

	AdvancedDrills = {
		id          = "AdvancedDrills",
		displayName = "Advanced Drills",
		description = "Drills produce +100% more minerals per tick.",
		cost        = 60,
		requires    = { "FasterDrills" },
		effect      = { type = "ProductionBoost", module = "Drill", multiplier = 2.0 },
		icon        = "⛏️",
	},

	BetterFishTraps = {
		id          = "BetterFishTraps",
		displayName = "Better Fish Traps",
		description = "Fish Traps catch +75% more food per tick.",
		cost        = 25,
		requires    = {},
		effect      = { type = "ProductionBoost", module = "FishTrap", multiplier = 1.75 },
		icon        = "🐟",
	},

	FishMarket = {
		id          = "FishMarket",
		displayName = "Fish Market",
		description = "Sell food at 3 coins each instead of 2.",
		cost        = 50,
		requires    = { "BetterFishTraps" },
		effect      = { type = "FoodSellRate", rate = 3 },
		icon        = "💰",
	},

	-- ── OXYGEN BRANCH ────────────────────────────────────────────────────────

	OxygenRecycling = {
		id          = "OxygenRecycling",
		displayName = "Oxygen Recycling",
		description = "Reduces oxygen drain by 30% while diving.",
		cost        = 30,
		requires    = {},
		effect      = { type = "OxygenDrainReduction", percent = 0.30 },
		icon        = "💨",
	},

	DeepBreathing = {
		id          = "DeepBreathing",
		displayName = "Deep Breathing",
		description = "Reduces oxygen drain by a further 50%.",
		cost        = 80,
		requires    = { "OxygenRecycling" },
		effect      = { type = "OxygenDrainReduction", percent = 0.50 },
		icon        = "💨",
	},

	-- ── DEFENSE BRANCH ───────────────────────────────────────────────────────

	ReinforcedHull = {
		id          = "ReinforcedHull",
		displayName = "Reinforced Hull",
		description = "All modules have +50% max HP.",
		cost        = 40,
		requires    = {},
		effect      = { type = "ModuleHPBoost", multiplier = 1.5 },
		icon        = "🛡️",
	},

	AutoRepair = {
		id          = "AutoRepair",
		displayName = "Auto Repair",
		description = "Modules slowly repair themselves over time.",
		cost        = 100,
		requires    = { "ReinforcedHull" },
		effect      = { type = "AutoRepair", hpPerTick = 2 },
		icon        = "🔧",
	},

	TurretOverclock = {
		id          = "TurretOverclock",
		displayName = "Turret Overclock",
		description = "Turrets fire 40% faster.",
		cost        = 60,
		requires    = { "ReinforcedHull" },
		effect      = { type = "TurretFireRateBoost", multiplier = 0.6 },
		icon        = "🔴",
	},

	-- ── POWER BRANCH ─────────────────────────────────────────────────────────

	EfficientPower = {
		id          = "EfficientPower",
		displayName = "Efficient Power",
		description = "All modules consume 25% less power.",
		cost        = 35,
		requires    = {},
		effect      = { type = "PowerConsumptionReduction", percent = 0.25 },
		icon        = "⚡",
	},

	PowerSurge = {
		id          = "PowerSurge",
		displayName = "Power Surge",
		description = "Solar panels and Thermal Vents produce +80% more power.",
		cost        = 90,
		requires    = { "EfficientPower" },
		effect      = { type = "ProductionBoost", module = "SolarPanel", multiplier = 1.8 },
		icon        = "⚡",
	},

	-- ── COMBAT BRANCH ────────────────────────────────────────────────────────

	SonarPulse = {
		id          = "SonarPulse",
		displayName = "Sonar Pulse",
		description = "Reveals all creatures near your base on the minimap.",
		cost        = 45,
		requires    = {},
		effect      = { type = "SonarReveal", radius = 200 },
		icon        = "📡",
	},

	CreatureRepellent = {
		id          = "CreatureRepellent",
		displayName = "Creature Repellent",
		description = "Creatures spawn 30% less frequently.",
		cost        = 120,
		requires    = { "SonarPulse" },
		effect      = { type = "SpawnRateReduction", percent = 0.30 },
		icon        = "🦑",
	},
}

-- Helper: get research by id
function ResearchData.Get(id)
	return ResearchData.Tree[id]
end

-- Helper: get all research as flat list
function ResearchData.GetAll()
	local list = {}
	for _, v in pairs(ResearchData.Tree) do
		table.insert(list, v)
	end
	return list
end

return ResearchData
