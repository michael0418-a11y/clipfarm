-- DataManager.server.lua
-- Handles saving and loading player data via DataStoreService
-- Place in ServerScriptService

local Players            = game:GetService("Players")
local DataStoreService   = game:GetService("DataStoreService")
local ReplicatedStorage  = game:GetService("ReplicatedStorage")
local RunService         = game:GetService("RunService")

local GameConfig = require(ReplicatedStorage:WaitForChild("GameConfig"))
local Remotes    = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local DataStore = DataStoreService:GetDataStore("UnderwaterTycoon_v1")

local DataManager = {}
local playerData  = {}  -- [userId] = data table

-- ── DEFAULT DATA ────────────────────────────────────────────────────────────

local function newPlayerData()
	return {
		-- Resources
		Minerals = GameConfig.PlayerDefaults.Minerals,
		Oxygen   = GameConfig.PlayerDefaults.Oxygen,
		Food     = GameConfig.PlayerDefaults.Food,
		Power    = GameConfig.PlayerDefaults.Power,
		Coins    = GameConfig.PlayerDefaults.Coins,

		-- Progression
		UnlockedZones    = { 1 },
		PlacedModules    = {},   -- array of { id, position, rotation, level }
		ResearchPoints   = 0,

		-- Stats
		TotalMined       = 0,
		CreaturesKilled  = 0,
		TimePlayed       = 0,

		-- Mode (set on first join or mode select)
		GameMode         = nil,
	}
end

-- ── LOAD ─────────────────────────────────────────────────────────────────────

function DataManager.Load(player)
	local key    = "player_" .. player.UserId
	local loaded = nil
	local success, err = pcall(function()
		loaded = DataStore:GetAsync(key)
	end)

	if success and loaded then
		-- Merge with defaults so new fields appear on old saves
		local defaults = newPlayerData()
		for k, v in pairs(defaults) do
			if loaded[k] == nil then
				loaded[k] = v
			end
		end
		playerData[player.UserId] = loaded
	else
		if not success then
			warn("[DataManager] Failed to load data for " .. player.Name .. ": " .. tostring(err))
		end
		playerData[player.UserId] = newPlayerData()
	end

	return playerData[player.UserId]
end

-- ── SAVE ─────────────────────────────────────────────────────────────────────

function DataManager.Save(player)
	local data = playerData[player.UserId]
	if not data then return end

	local key = "player_" .. player.UserId
	local success, err = pcall(function()
		DataStore:SetAsync(key, data)
	end)

	if success then
		local ev = Remotes.Get("DataSaved")
		if ev then ev:FireClient(player) end
	else
		warn("[DataManager] Failed to save data for " .. player.Name .. ": " .. tostring(err))
	end
end

-- ── GET / SET ─────────────────────────────────────────────────────────────────

function DataManager.Get(player)
	return playerData[player.UserId]
end

function DataManager.GetResource(player, resource)
	local data = DataManager.Get(player)
	return data and data[resource] or 0
end

function DataManager.SetResource(player, resource, amount)
	local data = DataManager.Get(player)
	if data then
		data[resource] = math.max(0, amount)
	end
end

function DataManager.AddResource(player, resource, amount)
	local data = DataManager.Get(player)
	if data then
		data[resource] = math.max(0, (data[resource] or 0) + amount)
	end
end

function DataManager.CanAfford(player, costs)
	local data = DataManager.Get(player)
	if not data then return false end
	for resource, amount in pairs(costs) do
		if (data[resource] or 0) < amount then
			return false
		end
	end
	return true
end

function DataManager.Deduct(player, costs)
	if not DataManager.CanAfford(player, costs) then return false end
	local data = DataManager.Get(player)
	for resource, amount in pairs(costs) do
		data[resource] = data[resource] - amount
	end
	return true
end

-- ── AUTO-SAVE LOOP ────────────────────────────────────────────────────────────

local saveInterval = GameConfig.Settings.DataSaveInterval
local elapsed      = 0

RunService.Heartbeat:Connect(function(dt)
	elapsed = elapsed + dt
	if elapsed >= saveInterval then
		elapsed = 0
		for _, player in ipairs(Players:GetPlayers()) do
			DataManager.Save(player)
		end
	end
end)

-- ── PLAYER EVENTS ────────────────────────────────────────────────────────────

Players.PlayerAdded:Connect(function(player)
	DataManager.Load(player)
end)

Players.PlayerRemoving:Connect(function(player)
	DataManager.Save(player)
	playerData[player.UserId] = nil
end)

-- Handle server shutdown gracefully
game:BindToClose(function()
	for _, player in ipairs(Players:GetPlayers()) do
		DataManager.Save(player)
	end
end)

return DataManager
