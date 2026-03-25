-- ZoneManager.server.lua
-- Handles zone unlocking: validates cost, updates data, fires events
-- Place in ServerScriptService

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local GameConfig = require(ReplicatedStorage:WaitForChild("GameConfig"))
local Remotes    = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local DataManager -- lazy

local ZoneManager = {}

-- ── UNLOCK ZONE ───────────────────────────────────────────────────────────────

Remotes.Get("UnlockZone").OnServerEvent:Connect(function(player, zoneIndex)
	local data = DataManager and DataManager.Get(player)
	if not data then return end

	local zone = GameConfig.Zones[zoneIndex]
	if not zone then return end

	-- Already unlocked?
	for _, z in ipairs(data.UnlockedZones) do
		if z == zoneIndex then
			Remotes.Get("ResourceError"):FireClient(player, "Zone already unlocked!")
			return
		end
	end

	-- Must unlock zones in order
	local prevZone = zoneIndex - 1
	if prevZone > 0 then
		local hasPrev = false
		for _, z in ipairs(data.UnlockedZones) do
			if z == prevZone then hasPrev = true break end
		end
		if not hasPrev then
			Remotes.Get("ResourceError"):FireClient(player, "Unlock " .. GameConfig.Zones[prevZone].name .. " first!")
			return
		end
	end

	-- Cost check (zone unlock costs Coins)
	if (data.Coins or 0) < zone.unlockCost then
		Remotes.Get("ResourceError"):FireClient(player, "Need " .. zone.unlockCost .. " Coins to unlock " .. zone.name)
		return
	end

	data.Coins = data.Coins - zone.unlockCost
	table.insert(data.UnlockedZones, zoneIndex)

	Remotes.Get("ZoneUnlocked"):FireClient(player, zoneIndex)
	Remotes.Get("Notification"):FireClient(player, {
		title   = "Zone Unlocked!",
		message = zone.name .. " is now accessible!",
		type    = "success",
	})
end)

-- ── QUERY UNLOCKED ZONES ─────────────────────────────────────────────────────

function ZoneManager.GetUnlockedZones(player)
	local data = DataManager and DataManager.Get(player)
	return data and data.UnlockedZones or { 1 }
end

function ZoneManager.IsZoneUnlocked(player, zoneIndex)
	for _, z in ipairs(ZoneManager.GetUnlockedZones(player)) do
		if z == zoneIndex then return true end
	end
	return false
end

task.defer(function()
	DataManager = require(script.Parent:WaitForChild("DataManager"))
end)

return ZoneManager
