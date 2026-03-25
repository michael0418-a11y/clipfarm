-- PressureSystem.server.lua
-- Damages modules that lack pressure shield coverage in deep zones
-- Place in ServerScriptService

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService        = game:GetService("RunService")
local Workspace         = game:GetService("Workspace")

local GameConfig  = require(ReplicatedStorage:WaitForChild("GameConfig"))
local ModuleData  = require(ReplicatedStorage:WaitForChild("Modules"):WaitForChild("ModuleData"))
local Remotes     = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local DataManager -- lazy
local BaseManager -- lazy

local PressureSystem = {}

local tickElapsed = 0

RunService.Heartbeat:Connect(function(dt)
	tickElapsed = tickElapsed + dt
	if tickElapsed < GameConfig.Settings.PressureDamageRate then return end
	tickElapsed = 0

	if not DataManager or not BaseManager then return end

	for _, player in ipairs(Players:GetPlayers()) do
		local data = DataManager.Get(player)
		if not data then continue end

		-- Build list of shield coverage spheres
		local shields = {}
		for _, placed in ipairs(data.PlacedModules) do
			if placed.id ~= "PressureShield" then continue end
			local modDef = ModuleData.Get("PressureShield")
			local level  = placed.level or 1
			local stats  = modDef.levelBonuses and modDef.levelBonuses[level] or modDef.stats
			local pos    = Vector3.new(placed.position[1], placed.position[2], placed.position[3])
			table.insert(shields, { position = pos, radius = stats.radius, resist = stats.pressureResist })
		end

		-- Check each module against zone pressure requirements
		for _, placed in ipairs(data.PlacedModules) do
			if placed.id == "PressureShield" then continue end

			local pos      = Vector3.new(placed.position[1], placed.position[2], placed.position[3])
			local depth    = math.max(0, -pos.Y)

			-- Find what zone this module is in
			local zoneLevel = 1
			for i, zone in ipairs(GameConfig.Zones) do
				if depth >= zone.minDepth and depth < zone.maxDepth then
					zoneLevel = i
					break
				end
			end

			local requiredResist = GameConfig.Zones[zoneLevel].pressureLevel
			if requiredResist == 0 then continue end  -- no pressure in Zone 1

			-- Check if covered by a shield with sufficient resistance
			local covered = false
			for _, shield in ipairs(shields) do
				local dist = (shield.position - pos).Magnitude
				if dist <= shield.radius and shield.resist >= requiredResist then
					covered = true
					break
				end
			end

			if not covered then
				-- Damage this module
				local dmg = GameConfig.Settings.PressureDamageAmt
				placed.hp = math.max(0, (placed.hp or 100) - dmg)

				Remotes.Get("ModuleDamaged"):FireClient(player, placed.instanceId, placed.hp)
				Remotes.Get("Notification"):FireClient(player, {
					title   = "⚠ Pressure Damage!",
					message = placed.instanceId .. " needs a Pressure Shield!",
					type    = "warning",
				})

				if placed.hp <= 0 then
					Remotes.Get("ModuleDestroyed"):FireClient(player, placed.instanceId)
					BaseManager.DamageModule(player, placed.instanceId, 99999)
				end
			end
		end
	end
end)

task.defer(function()
	DataManager = require(script.Parent:WaitForChild("DataManager"))
	BaseManager = require(script.Parent:WaitForChild("BaseManager"))
end)

return PressureSystem
