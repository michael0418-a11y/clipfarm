-- PrestigeSystem.server.lua
-- Endgame prestige: reset progress for permanent multiplier bonuses and a badge
-- Place in ServerScriptService

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local GameConfig = require(ReplicatedStorage:WaitForChild("GameConfig"))
local Remotes    = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local DataManager -- lazy

local PrestigeSystem = {}

-- ── PRESTIGE LEVELS ───────────────────────────────────────────────────────────

local PRESTIGE_LEVELS = {
	{
		level       = 1,
		displayName = "⭐ Deep Diver",
		requirement = { Coins = 100000, UnlockedAllZones = true },
		bonus       = { productionMult = 1.25, description = "+25% all production" },
	},
	{
		level       = 2,
		displayName = "🌟 Abyss Walker",
		requirement = { Coins = 500000, UnlockedAllZones = true, CreaturesKilled = 500 },
		bonus       = { productionMult = 1.60, description = "+60% all production" },
	},
	{
		level       = 3,
		displayName = "💎 Ocean Master",
		requirement = { Coins = 2000000, UnlockedAllZones = true, CreaturesKilled = 2000 },
		bonus       = { productionMult = 2.10, description = "+110% all production" },
	},
	{
		level       = 4,
		displayName = "👑 Leviathan",
		requirement = { Coins = 10000000, UnlockedAllZones = true, CreaturesKilled = 10000 },
		bonus       = { productionMult = 3.00, description = "+200% all production" },
	},
	{
		level       = 5,
		displayName = "🌊 Sea God",
		requirement = { Coins = 50000000, UnlockedAllZones = true, CreaturesKilled = 50000 },
		bonus       = { productionMult = 5.00, description = "+400% all production" },
	},
}

-- ── REMOTE SETUP ─────────────────────────────────────────────────────────────

local PrestigeRequest = Instance.new("RemoteEvent")
PrestigeRequest.Name  = "PrestigeRequest"
PrestigeRequest.Parent = ReplicatedStorage:WaitForChild("Remotes")

local GetPrestigeInfo = Instance.new("RemoteFunction")
GetPrestigeInfo.Name  = "GetPrestigeInfo"
GetPrestigeInfo.Parent = ReplicatedStorage:WaitForChild("Remotes")

-- ── HELPER: CHECK REQUIREMENTS ────────────────────────────────────────────────

local function meetsRequirements(data, req)
	if req.Coins and (data.Coins or 0) < req.Coins then
		return false, "Need " .. req.Coins .. " Coins"
	end
	if req.CreaturesKilled and (data.CreaturesKilled or 0) < req.CreaturesKilled then
		return false, "Need " .. req.CreaturesKilled .. " Creature Kills"
	end
	if req.UnlockedAllZones then
		if #(data.UnlockedZones or {}) < #GameConfig.Zones then
			return false, "Must unlock ALL zones first"
		end
	end
	return true, nil
end

-- ── PRESTIGE HANDLER ─────────────────────────────────────────────────────────

PrestigeRequest.OnServerEvent:Connect(function(player)
	if not DataManager then return end
	local data = DataManager.Get(player)
	if not data then return end

	local currentPrestige = data.PrestigeLevel or 0
	local nextLevel       = currentPrestige + 1
	local prestigeDef     = PRESTIGE_LEVELS[nextLevel]

	if not prestigeDef then
		Remotes.Get("ResourceError"):FireClient(player, "Already at max prestige!")
		return
	end

	local ok, reason = meetsRequirements(data, prestigeDef.requirement)
	if not ok then
		Remotes.Get("ResourceError"):FireClient(player, "Cannot prestige: " .. reason)
		return
	end

	-- ── RESET ────────────────────────────────────────────────────────────────
	-- Keep: PrestigeLevel, TotalMined, CreaturesKilled, UnlockedResearch
	-- Reset: Minerals, Oxygen, Food, Power, Coins, UnlockedZones, PlacedModules, ResearchPoints

	data.PrestigeLevel      = nextLevel
	data.PrestigeMult       = prestigeDef.bonus.productionMult

	-- Reset resources
	data.Minerals           = GameConfig.PlayerDefaults.Minerals
	data.Oxygen             = GameConfig.PlayerDefaults.Oxygen
	data.Food               = GameConfig.PlayerDefaults.Food
	data.Power              = GameConfig.PlayerDefaults.Power
	data.Coins              = 0
	data.ResearchPoints     = 0

	-- Reset progression
	data.UnlockedZones      = { 1 }
	data.PlacedModules      = {}

	-- Rebuild world: clear old base parts
	local basesFolder = workspace:FindFirstChild("Bases")
	if basesFolder then
		local playerFolder = basesFolder:FindFirstChild(tostring(player.UserId))
		if playerFolder then
			playerFolder:ClearAllChildren()
		end
	end

	-- Re-place starter pod with prestige bonus in name
	local BaseManager = require(script.Parent:WaitForChild("BaseManager"))
	BaseManager.PlaceStarterPod(player)

	-- Notify
	Remotes.Get("Notification"):FireClient(player, {
		title   = "PRESTIGE " .. nextLevel .. "!",
		message = prestigeDef.displayName .. " — " .. prestigeDef.bonus.description,
		type    = "success",
	})

	-- Server-wide announcement
	for _, p in ipairs(Players:GetPlayers()) do
		if p ~= player then
			Remotes.Get("Notification"):FireClient(p, {
				title   = "🌟 Prestige!",
				message = player.Name .. " achieved " .. prestigeDef.displayName .. "!",
				type    = "info",
			})
		end
	end

	print("[PrestigeSystem] " .. player.Name .. " prestiged to level " .. nextLevel)
end)

-- ── GET PRESTIGE INFO ─────────────────────────────────────────────────────────

GetPrestigeInfo.OnServerInvoke = function(player)
	if not DataManager then return {} end
	local data = DataManager.Get(player)
	if not data then return {} end

	local currentLevel = data.PrestigeLevel or 0
	local nextLevel    = currentLevel + 1
	local nextDef      = PRESTIGE_LEVELS[nextLevel]

	return {
		currentLevel = currentLevel,
		currentMult  = data.PrestigeMult or 1,
		nextLevel    = nextDef,
		allLevels    = PRESTIGE_LEVELS,
	}
end

-- ── PRODUCTION MULT GETTER (used by ResourceManager) ─────────────────────────

function PrestigeSystem.GetProductionMult(player)
	if not DataManager then return 1 end
	local data = DataManager.Get(player)
	return (data and data.PrestigeMult) or 1
end

task.defer(function()
	DataManager = require(script.Parent:WaitForChild("DataManager"))
end)

return PrestigeSystem
