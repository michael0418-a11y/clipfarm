-- ResourceManager.server.lua
-- Handles AFK resource generation, oxygen drain, food/coin conversion
-- Place in ServerScriptService as a ModuleScript

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService        = game:GetService("RunService")

local GameConfig  = require(ReplicatedStorage:WaitForChild("GameConfig"))
local ModuleData  = require(ReplicatedStorage:WaitForChild("Modules"):WaitForChild("ModuleData"))

local DataManager -- required below to avoid circular dependency

local ResourceManager = {}
local activeLoops     = {}  -- [userId] = true/false

-- ── CALCULATE PRODUCTION ─────────────────────────────────────────────────────
-- Reads placed modules from player data and totals up per-tick production

local function calcProduction(data)
	local prod = {
		Oxygen         = 0,
		Minerals       = 0,
		Food           = 0,
		Power          = 0,
		ResearchPoints = 0,
	}

	for _, placed in ipairs(data.PlacedModules) do
		local modDef = ModuleData.Get(placed.id)
		if modDef and modDef.production then
			local level   = placed.level or 1
			local bonuses = modDef.levelBonuses and modDef.levelBonuses[level]
			if bonuses then
				-- Find the production key (e.g. OxygenPerTick → Oxygen)
				for k, v in pairs(bonuses) do
					local resource = k:gsub("PerTick", "")
					if prod[resource] ~= nil then
						prod[resource] = prod[resource] + v
					end
				end
			end
		end
	end

	return prod
end

-- ── OXYGEN DRAIN ─────────────────────────────────────────────────────────────

local oxygenElapsed = 0

RunService.Heartbeat:Connect(function(dt)
	oxygenElapsed = oxygenElapsed + dt
	if oxygenElapsed < GameConfig.Settings.OxygenTickRate then return end
	oxygenElapsed = 0

	if not DataManager then return end

	for _, player in ipairs(Players:GetPlayers()) do
		local data = DataManager.Get(player)
		if not data then continue end

		local char = player.Character
		if not char then continue end

		local hrp = char:FindFirstChild("HumanoidRootPart")
		if not hrp then continue end

		-- Only drain oxygen if underwater (below water level, y < 0)
		if hrp.Position.Y < 0 then
			local drain = GameConfig.Settings.OxygenDrainPerTick
			data.Oxygen = math.max(0, data.Oxygen - drain)

			if data.Oxygen <= 0 then
				-- Drown the player
				local hum = char:FindFirstChildOfClass("Humanoid")
				if hum then
					hum.Health = 0
				end
			end
		end
	end
end)

-- ── AFK PRODUCTION LOOP ───────────────────────────────────────────────────────

local resourceElapsed = 0

RunService.Heartbeat:Connect(function(dt)
	resourceElapsed = resourceElapsed + dt
	if resourceElapsed < GameConfig.Settings.ResourceTickRate then return end
	resourceElapsed = 0

	if not DataManager then return end

	for _, player in ipairs(Players:GetPlayers()) do
		if not activeLoops[player.UserId] then continue end

		local data = DataManager.Get(player)
		if not data then continue end

		local prod = calcProduction(data)

		-- Add production to stored resources
		data.Minerals       = (data.Minerals       or 0) + prod.Minerals
		data.Food           = (data.Food           or 0) + prod.Food
		data.Power          = (data.Power          or 0) + prod.Power
		data.ResearchPoints = (data.ResearchPoints or 0) + prod.ResearchPoints

		-- Cap oxygen at max storage (from StarterPod level)
		local maxOxygen = GameConfig.PlayerDefaults.MaxOxygen
		for _, placed in ipairs(data.PlacedModules) do
			if placed.id == "StarterPod" then
				local modDef = ModuleData.Get("StarterPod")
				local bonuses = modDef.levelBonuses and modDef.levelBonuses[placed.level or 1]
				if bonuses and bonuses.OxygenStorage then
					maxOxygen = bonuses.OxygenStorage
				end
			end
		end
		data.Oxygen = math.min(maxOxygen, (data.Oxygen or 0) + prod.Oxygen)

		-- Convert Food → Coins (1 food = 2 coins, sell automatically)
		if data.Food > 100 then
			local sellAmount  = math.floor(data.Food - 100)
			data.Food         = data.Food - sellAmount
			data.Coins        = (data.Coins or 0) + (sellAmount * 2)
		end
	end
end)

-- ── MANUAL MINING ─────────────────────────────────────────────────────────────
-- Call when player clicks a mineral node in the world

function ResourceManager.MineNode(player, mineralAmount)
	if not DataManager then return end
	local data = DataManager.Get(player)
	if not data then return end
	data.Minerals    = (data.Minerals    or 0) + mineralAmount
	data.TotalMined  = (data.TotalMined  or 0) + mineralAmount
end

-- ── START / STOP FOR PLAYER ───────────────────────────────────────────────────

function ResourceManager.StartForPlayer(player)
	activeLoops[player.UserId] = true
end

function ResourceManager.StopForPlayer(player)
	activeLoops[player.UserId] = nil
end

-- Lazy-load DataManager to avoid circular requires
task.defer(function()
	DataManager = require(script.Parent:WaitForChild("DataManager"))
end)

return ResourceManager
