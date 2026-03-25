-- CombatManager.server.lua
-- Spawns sea creatures, manages AI movement and attacks on player bases
-- Place in ServerScriptService

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace         = game:GetService("Workspace")
local RunService        = game:GetService("RunService")

local GameConfig    = require(ReplicatedStorage:WaitForChild("GameConfig"))
local CreatureData  = require(ReplicatedStorage:WaitForChild("Modules"):WaitForChild("CreatureData"))
local Remotes       = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local DataManager -- lazy
local BaseManager -- lazy

local CombatManager = {}

-- Folder for creature models
local creaturesFolder = Workspace:FindFirstChild("Creatures") or Instance.new("Folder", Workspace)
creaturesFolder.Name  = "Creatures"

-- Active creatures: [creatureId] = { data, part, target(player), hp, attackCooldown }
local activeCreatures  = {}
local creatureIdCounter = 0

-- Spawn timers per player per zone: [userId_zone] = elapsed
local spawnTimers = {}

-- ── SPAWN CREATURE ────────────────────────────────────────────────────────────

local function spawnCreature(player, zoneLevel)
	local creatureDef = CreatureData.PickRandom(zoneLevel)
	if not creatureDef then return end

	local data = DataManager and DataManager.Get(player)
	if not data then return end

	-- Spawn position: offset from the player's base pod
	local baseParts = BaseManager and BaseManager.GetBaseParts(player) or {}
	if #baseParts == 0 then return end

	local podPart    = baseParts[1]  -- target the first module (usually pod)
	local spawnRadius = 150
	local angle      = math.random() * math.pi * 2
	local spawnPos   = podPart.Position + Vector3.new(
		math.cos(angle) * spawnRadius,
		math.random(-20, 20),
		math.sin(angle) * spawnRadius
	)

	creatureIdCounter = creatureIdCounter + 1
	local cid = "creature_" .. creatureIdCounter

	-- Build part
	local part        = Instance.new("Part")
	part.Name         = cid
	part.Size         = creatureDef.size
	part.Color        = creatureDef.color
	part.Anchored     = false
	part.CanCollide   = true
	part.Position     = spawnPos
	part.Material     = Enum.Material.SmoothPlastic
	part.Parent       = creaturesFolder

	-- Billboard
	local bb   = Instance.new("BillboardGui", part)
	bb.Name    = "CreatureHud"
	bb.Size    = UDim2.new(0, 110, 0, 44)
	bb.StudsOffset = Vector3.new(0, creatureDef.size.Y / 2 + 1, 0)
	bb.AlwaysOnTop = true

	local lbl  = Instance.new("TextLabel", bb)
	lbl.Name   = "NameLabel"
	lbl.Size   = UDim2.new(1, 0, 0.5, 0)
	lbl.BackgroundTransparency = 1
	lbl.Text   = creatureDef.displayName
	lbl.TextColor3 = Color3.fromRGB(255, 80, 80)
	lbl.TextScaled = true
	lbl.Font   = Enum.Font.GothamBold

	-- HP bar background
	local hpBg = Instance.new("Frame", bb)
	hpBg.Name  = "HpBg"
	hpBg.Size  = UDim2.new(1, -4, 0, 8)
	hpBg.Position = UDim2.new(0, 2, 0.55, 2)
	hpBg.BackgroundColor3 = Color3.fromRGB(60, 0, 0)
	hpBg.BorderSizePixel  = 0
	local hpBgCorner = Instance.new("UICorner", hpBg)
	hpBgCorner.CornerRadius = UDim.new(0, 3)

	local hpFill = Instance.new("Frame", hpBg)
	hpFill.Name  = "HpFill"
	hpFill.Size  = UDim2.new(1, 0, 1, 0)
	hpFill.BackgroundColor3 = Color3.fromRGB(220, 50, 50)
	hpFill.BorderSizePixel  = 0
	local hpFillCorner = Instance.new("UICorner", hpFill)
	hpFillCorner.CornerRadius = UDim.new(0, 3)

	-- Attributes
	part:SetAttribute("CreatureId",   cid)
	part:SetAttribute("CreatureType", creatureDef.id)
	part:SetAttribute("HP",           creatureDef.health)
	part:SetAttribute("MaxHP",        creatureDef.health)

	activeCreatures[cid] = {
		def             = creatureDef,
		part            = part,
		targetPlayer    = player,
		hp              = creatureDef.health,
		attackCooldown  = 0,
		rewardGiven     = false,
	}

	Remotes.Get("CreatureSpawned"):FireClient(player, {
		id       = cid,
		type     = creatureDef.id,
		position = { spawnPos.X, spawnPos.Y, spawnPos.Z },
	})

	Remotes.Get("BaseUnderAttack"):FireClient(player)
end

-- ── AI MOVEMENT + ATTACK LOOP ─────────────────────────────────────────────────

local aiElapsed = 0

RunService.Heartbeat:Connect(function(dt)
	aiElapsed = aiElapsed + dt

	-- Only run AI at ~20 fps to save performance
	if aiElapsed < 0.05 then return end
	local delta   = aiElapsed
	aiElapsed     = 0

	for cid, creature in pairs(activeCreatures) do
		local part = creature.part
		if not part or not part.Parent then
			activeCreatures[cid] = nil
			continue
		end

		local player = creature.targetPlayer
		local baseParts = BaseManager and BaseManager.GetBaseParts(player) or {}
		if #baseParts == 0 then continue end

		-- Find nearest base part
		local nearest, nearestDist = nil, math.huge
		for _, bp in ipairs(baseParts) do
			local dist = (bp.Position - part.Position).Magnitude
			if dist < nearestDist then
				nearest     = bp
				nearestDist = dist
			end
		end
		if not nearest then continue end

		-- Move toward target
		local dir    = (nearest.Position - part.Position).Unit
		local speed  = creature.def.speed
		local vel    = dir * speed
		part.AssemblyLinearVelocity = Vector3.new(vel.X, vel.Y, vel.Z)

		-- Attack if in range
		creature.attackCooldown = math.max(0, creature.attackCooldown - delta)
		if nearestDist <= creature.def.attackRange and creature.attackCooldown <= 0 then
			creature.attackCooldown = 2.0  -- 2 second attack cooldown

			local instanceId = nearest:GetAttribute("InstanceId")
			if instanceId and BaseManager then
				BaseManager.DamageModule(player, instanceId, creature.def.damage)
			end
		end
	end
end)

-- ── CREATURE SPAWN TICK ───────────────────────────────────────────────────────

local spawnElapsed = 0

RunService.Heartbeat:Connect(function(dt)
	spawnElapsed = spawnElapsed + dt
	if spawnElapsed < GameConfig.Settings.CreatureSpawnRate then return end
	spawnElapsed = 0

	if not DataManager then return end

	for _, player in ipairs(Players:GetPlayers()) do
		local data = DataManager.Get(player)
		if not data or not data.GameMode then continue end

		-- Spawn one wave per unlocked zone
		for _, zoneIndex in ipairs(data.UnlockedZones) do
			spawnCreature(player, zoneIndex)
		end
	end
end)

-- ── DAMAGE CREATURE (called when player/turret shoots) ────────────────────────

function CombatManager.DamageCreature(creatureId, damage, player)
	local creature = activeCreatures[creatureId]
	if not creature then
		-- Boss creatures are tracked via part attributes (spawned by BossAnnouncer)
		local creaturesFolder = Workspace:FindFirstChild("Creatures")
		if creaturesFolder then
			for _, part in ipairs(creaturesFolder:GetChildren()) do
				if part:GetAttribute("CreatureId") == creatureId then
					local newHp = math.max(0, (part:GetAttribute("HP") or 0) - damage)
					part:SetAttribute("HP", newHp)
					return
				end
			end
		end
		return
	end

	creature.hp = math.max(0, creature.hp - damage)
	creature.part:SetAttribute("HP", creature.hp)

	-- Update billboard HP bar
	local bb = creature.part:FindFirstChild("CreatureHud")
	if bb then
		local hpFill = bb:FindFirstChild("HpBg") and bb.HpBg:FindFirstChild("HpFill")
		if hpFill then
			hpFill.Size = UDim2.new(math.max(0, creature.hp / creature.def.health), 0, 1, 0)
		end
	end

	if creature.hp <= 0 then
		-- Give reward to player
		if not creature.rewardGiven and DataManager then
			creature.rewardGiven = true
			local reward = creature.def.reward
			for resource, amount in pairs(reward) do
				DataManager.AddResource(player, resource, amount)
			end
			local data = DataManager.Get(player)
			if data then
				data.CreaturesKilled = (data.CreaturesKilled or 0) + 1
				-- Immediate resource push so client sees reward instantly
				Remotes.Get("ResourceUpdate"):FireClient(player, {
					Minerals       = data.Minerals,
					Oxygen         = data.Oxygen,
					Food           = data.Food,
					Power          = data.Power,
					Coins          = data.Coins,
					ResearchPoints = data.ResearchPoints,
				})
			end
			Remotes.Get("CreatureDied"):FireClient(player, creatureId, reward)
		end
		creature.part:Destroy()
		activeCreatures[creatureId] = nil
	end
end

-- ── PLAYER SHOOTS (from client remote) ───────────────────────────────────────

-- Players can damage creatures by clicking on them
local ShootCreature = Instance.new("RemoteEvent")
ShootCreature.Name  = "ShootCreature"
ShootCreature.Parent = ReplicatedStorage:WaitForChild("Remotes")

ShootCreature.OnServerEvent:Connect(function(player, creatureId, damage)
	-- Sanity cap: player can't send arbitrary damage
	local clampedDamage = math.min(damage or 10, 50)
	CombatManager.DamageCreature(creatureId, clampedDamage, player)
end)

-- Lazy loads
task.defer(function()
	DataManager = require(script.Parent:WaitForChild("DataManager"))
	BaseManager = require(script.Parent:WaitForChild("BaseManager"))
end)

return CombatManager
