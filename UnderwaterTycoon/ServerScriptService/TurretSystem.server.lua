-- TurretSystem.server.lua
-- Auto-targeting turrets that shoot nearby sea creatures
-- Integrates with BaseManager (turret modules) and CombatManager (creatures)
-- Place in ServerScriptService

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService        = game:GetService("RunService")
local Workspace         = game:GetService("Workspace")

local GameConfig  = require(ReplicatedStorage:WaitForChild("GameConfig"))
local ModuleData  = require(ReplicatedStorage:WaitForChild("Modules"):WaitForChild("ModuleData"))
local Remotes     = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local DataManager    -- lazy
local BaseManager    -- lazy
local CombatManager  -- lazy

local TurretSystem = {}

-- Active turret cooldowns: [instanceId] = timeUntilNextShot
local turretCooldowns = {}

-- Visual laser effect (brief Part)
local function fireLaser(fromPos, toPos)
	local mid    = (fromPos + toPos) / 2
	local len    = (toPos - fromPos).Magnitude
	local laser  = Instance.new("Part")
	laser.Name   = "TurretLaser"
	laser.Anchored     = true
	laser.CanCollide   = false
	laser.CastShadow   = false
	laser.Size         = Vector3.new(0.15, 0.15, len)
	laser.CFrame       = CFrame.lookAt(mid, toPos) * CFrame.new(0, 0, -len / 2)
	laser.Color        = Color3.fromRGB(255, 80, 80)
	laser.Material     = Enum.Material.Neon
	laser.Transparency = 0.3
	laser.Parent       = Workspace

	game:GetService("Debris"):AddItem(laser, 0.08)
end

-- ── TURRET AI LOOP ────────────────────────────────────────────────────────────

local aiElapsed = 0

RunService.Heartbeat:Connect(function(dt)
	aiElapsed = aiElapsed + dt
	if aiElapsed < 0.1 then return end  -- run at ~10 fps
	local delta = aiElapsed
	aiElapsed   = 0

	if not DataManager or not BaseManager or not CombatManager then return end

	for _, player in ipairs(Players:GetPlayers()) do
		local data = DataManager.Get(player)
		if not data then continue end

		-- Find all placed turrets for this player
		for _, placed in ipairs(data.PlacedModules) do
			if placed.id ~= "Turret" then continue end

			local instanceId = placed.instanceId
			turretCooldowns[instanceId] = (turretCooldowns[instanceId] or 0) - delta

			if turretCooldowns[instanceId] > 0 then continue end

			-- Get turret world position
			local baseParts = BaseManager.GetBaseParts(player)
			local turretPart = nil
			for _, p in ipairs(baseParts) do
				if p:GetAttribute("InstanceId") == instanceId then
					turretPart = p
					break
				end
			end
			if not turretPart then continue end

			-- Get turret stats from level
			local level      = placed.level or 1
			local modDef     = ModuleData.Get("Turret")
			local stats      = modDef.levelBonuses and modDef.levelBonuses[level] or modDef.stats
			local range      = stats.range
			local damage     = stats.damage
			local fireRate   = stats.fireRate

			-- Find nearest creature in range
			local creaturesFolder = Workspace:FindFirstChild("Creatures")
			if not creaturesFolder then continue end

			local nearest, nearestDist, nearestId = nil, math.huge, nil
			for _, creaturePart in ipairs(creaturesFolder:GetChildren()) do
				local dist = (creaturePart.Position - turretPart.Position).Magnitude
				if dist < range and dist < nearestDist then
					nearest     = creaturePart
					nearestDist = dist
					nearestId   = creaturePart:GetAttribute("CreatureId")
				end
			end

			if nearest and nearestId then
				-- Fire!
				turretCooldowns[instanceId] = fireRate
				fireLaser(turretPart.Position, nearest.Position)
				CombatManager.DamageCreature(nearestId, damage, player)
			end
		end
	end
end)

-- Clean up cooldowns when modules are removed (client → server remove request)
Remotes.Get("RemoveModule").OnServerEvent:Connect(function(player, instanceId)
	turretCooldowns[instanceId] = nil
end)

task.defer(function()
	DataManager   = require(script.Parent:WaitForChild("DataManager"))
	BaseManager   = require(script.Parent:WaitForChild("BaseManager"))
	CombatManager = require(script.Parent:WaitForChild("CombatManager"))
end)

return TurretSystem
