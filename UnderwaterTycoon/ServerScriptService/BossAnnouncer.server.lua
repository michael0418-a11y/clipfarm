-- BossAnnouncer.server.lua
-- Manages boss spawning on timers and server-wide announcements
-- Also handles the player "challenge" to summon a boss early
-- Place in ServerScriptService as a Script

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace         = game:GetService("Workspace")
local RunService        = game:GetService("RunService")

local CreatureData = require(ReplicatedStorage:WaitForChild("Modules"):WaitForChild("CreatureData"))
local Remotes      = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local DataManager    -- lazy
local CombatManager  -- lazy
local BaseManager    -- lazy

-- ── REMOTE SETUP ─────────────────────────────────────────────────────────────

local BossAnnounce = Instance.new("RemoteEvent")
BossAnnounce.Name  = "BossAnnounce"
BossAnnounce.Parent = ReplicatedStorage:WaitForChild("Remotes")

local SummonBoss = Instance.new("RemoteEvent")
SummonBoss.Name  = "SummonBoss"
SummonBoss.Parent = ReplicatedStorage:WaitForChild("Remotes")

-- ── BOSS SPAWN TIMERS ─────────────────────────────────────────────────────────

local bossTimers = {}  -- { bossId = secondsUntilSpawn }

-- Initialize timers from CreatureData
for _, creature in pairs(CreatureData.Creatures) do
	if creature.isBoss and creature.spawnInterval then
		bossTimers[creature.id] = creature.spawnInterval
	end
end

-- Track active bosses per player
local activeBosses = {}  -- [userId_bossId] = true

-- ── SPAWN BOSS ────────────────────────────────────────────────────────────────

local function spawnBossForPlayer(player, bossDef)
	local key = tostring(player.UserId) .. "_" .. bossDef.id
	if activeBosses[key] then return end  -- already active
	activeBosses[key] = true

	if not BaseManager then return end
	local baseParts = BaseManager.GetBaseParts(player)
	if #baseParts == 0 then return end

	local podPart    = baseParts[1]
	local angle      = math.random() * math.pi * 2
	local spawnPos   = podPart.Position + Vector3.new(
		math.cos(angle) * 300,
		math.random(-30, 30),
		math.sin(angle) * 300
	)

	-- Build boss part
	local creaturesFolder = Workspace:FindFirstChild("Creatures")
	                    or Instance.new("Folder", Workspace)
	creaturesFolder.Name  = "Creatures"

	local part           = Instance.new("Part", creaturesFolder)
	part.Name            = "BOSS_" .. bossDef.id
	part.Size            = bossDef.size
	part.Color           = bossDef.color
	part.Anchored        = false
	part.CanCollide      = true
	part.Position        = spawnPos
	part.Material        = Enum.Material.Neon

	-- Pulsing glow
	local selBox         = Instance.new("SelectionBox", part)
	selBox.Adornee       = part
	selBox.Color3        = Color3.fromRGB(255, 0, 100)
	selBox.LineThickness = 0.15
	selBox.SurfaceTransparency = 0.7

	-- Billboard
	local bb   = Instance.new("BillboardGui", part)
	bb.Size    = UDim2.new(0, 200, 0, 50)
	bb.StudsOffset = Vector3.new(0, bossDef.size.Y / 2 + 3, 0)
	local lbl  = Instance.new("TextLabel", bb)
	lbl.Size   = UDim2.new(1, 0, 1, 0)
	lbl.BackgroundTransparency = 1
	lbl.Text   = "💀 " .. bossDef.displayName
	lbl.TextColor3 = Color3.fromRGB(255, 50, 50)
	lbl.TextScaled = true
	lbl.Font   = Enum.Font.GothamBold

	-- HP bar billboard
	local hpBb   = Instance.new("BillboardGui", part)
	hpBb.Size    = UDim2.new(0, 180, 0, 20)
	hpBb.StudsOffset = Vector3.new(0, bossDef.size.Y / 2 + 1, 0)
	local hpBg   = Instance.new("Frame", hpBb)
	hpBg.Size    = UDim2.new(1, 0, 1, 0)
	hpBg.BackgroundColor3 = Color3.fromRGB(30, 0, 0)
	hpBg.BorderSizePixel  = 0
	local hpFill = Instance.new("Frame", hpBg)
	hpFill.Name  = "Fill"
	hpFill.Size  = UDim2.new(1, 0, 1, 0)
	hpFill.BackgroundColor3 = Color3.fromRGB(200, 0, 0)
	hpFill.BorderSizePixel  = 0

	-- Attributes
	part:SetAttribute("CreatureId",   "BOSS_" .. bossDef.id .. "_" .. player.UserId)
	part:SetAttribute("CreatureType", bossDef.id)
	part:SetAttribute("HP",           bossDef.health)
	part:SetAttribute("MaxHP",        bossDef.health)
	part:SetAttribute("IsBoss",       true)

	-- Register in CombatManager
	if CombatManager then
		-- Inject into active creatures manually
		-- (CombatManager.activeCreatures is internal, so we use DamageCreature on death)
	end

	-- Announce to all players
	BossAnnounce:FireAllClients({
		bossName   = bossDef.displayName,
		playerName = player.Name,
		zone       = bossDef.zone,
	})

	-- Simple AI: move toward nearest base part
	local aiConn
	aiConn = RunService.Heartbeat:Connect(function(dt)
		if not part or not part.Parent then
			activeBosses[key] = nil
			aiConn:Disconnect()
			return
		end

		local hp = part:GetAttribute("HP") or 0
		if hp <= 0 then
			-- Boss defeated
			activeBosses[key] = nil
			aiConn:Disconnect()

			-- Give reward
			if DataManager then
				local reward = bossDef.reward
				for res, amt in pairs(reward) do
					DataManager.AddResource(player, res, amt)
				end
			end

			BossAnnounce:FireAllClients({
				bossName   = bossDef.displayName,
				playerName = player.Name,
				defeated   = true,
			})
			part:Destroy()
			return
		end

		-- Update HP bar
		local maxHp = part:GetAttribute("MaxHP") or 1
		if hpFill and hpFill.Parent then
			hpFill.Size = UDim2.new(math.clamp(hp / maxHp, 0, 1), 0, 1, 0)
		end

		-- Move toward nearest base part
		if not BaseManager then return end
		local parts = BaseManager.GetBaseParts(player)
		if #parts == 0 then return end

		local nearest, nearestDist = parts[1], math.huge
		for _, bp in ipairs(parts) do
			local d = (bp.Position - part.Position).Magnitude
			if d < nearestDist then nearest = bp; nearestDist = d end
		end

		local dir = (nearest.Position - part.Position).Unit
		part.AssemblyLinearVelocity = dir * bossDef.speed

		-- Attack
		if nearestDist <= bossDef.attackRange then
			local iid = nearest:GetAttribute("InstanceId")
			if iid and math.random() < 0.05 then  -- ~5% chance per frame at ~20fps = ~1/s
				if BaseManager then
					BaseManager.DamageModule(player, iid, bossDef.damage * dt * 20)
				end
			end
		end
	end)
end

-- ── BOSS TIMER LOOP ───────────────────────────────────────────────────────────

local timerElapsed = 0
RunService.Heartbeat:Connect(function(dt)
	timerElapsed = timerElapsed + dt
	if timerElapsed < 1 then return end
	timerElapsed = 0

	for bossId, timeLeft in pairs(bossTimers) do
		bossTimers[bossId] = timeLeft - 1

		if bossTimers[bossId] <= 60 then
			-- 60s warning
			if math.floor(timeLeft) == 61 then
				local bossDef = CreatureData.Creatures[bossId]
				if bossDef then
					BossAnnounce:FireAllClients({
						bossName  = bossDef.displayName,
						countdown = 60,
					})
				end
			end
		end

		if bossTimers[bossId] <= 0 then
			bossTimers[bossId] = CreatureData.Creatures[bossId].spawnInterval

			local bossDef = CreatureData.Creatures[bossId]
			if not bossDef then continue end

			-- Spawn for all eligible players
			if DataManager then
				for _, player in ipairs(Players:GetPlayers()) do
					local data = DataManager.Get(player)
					if not data or not data.GameMode then continue end

					-- Only spawn Kraken for Zone 3+ players, Titan for Zone 4 players
					local eligible = false
					for _, z in ipairs(data.UnlockedZones or {}) do
						if z >= bossDef.zone then eligible = true; break end
					end

					if eligible then
						spawnBossForPlayer(player, bossDef)
					end
				end
			end
		end
	end
end)

-- ── MANUAL SUMMON (player can spend Coins to summon early) ───────────────────

SummonBoss.OnServerEvent:Connect(function(player, bossId)
	local bossDef = CreatureData.Creatures[bossId]
	if not bossDef or not bossDef.isBoss then return end

	local summonCost = math.floor(bossDef.reward.Coins * 0.1)
	if DataManager then
		local data = DataManager.Get(player)
		if not data or (data.Coins or 0) < summonCost then
			Remotes.Get("ResourceError"):FireClient(player,
				"Summoning " .. bossDef.displayName .. " costs " .. summonCost .. " Coins!")
			return
		end
		DataManager.Deduct(player, { Coins = summonCost })
	end

	spawnBossForPlayer(player, bossDef)
end)

-- ── CLIENT: BOSS ANNOUNCE GUI ─────────────────────────────────────────────────
-- (Handled client-side in BossAnnouncerClient.client.lua)

task.defer(function()
	DataManager   = require(script.Parent:WaitForChild("DataManager"))
	CombatManager = require(script.Parent:WaitForChild("CombatManager"))
	BaseManager   = require(script.Parent:WaitForChild("BaseManager"))
end)

print("[BossAnnouncer] Boss system initialized.")
