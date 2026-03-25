-- PlayerController.client.lua
-- Handles player movement, diving, oxygen HUD updates, depth tracking
-- Place in StarterPlayer/StarterPlayerScripts as a LocalScript

local Players           = game:GetService("Players")
local UserInputService  = game:GetService("UserInputService")
local RunService        = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService      = game:GetService("TweenService")

local GameConfig = require(ReplicatedStorage:WaitForChild("GameConfig"))
local Remotes    = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local player    = Players.LocalPlayer
local mouse     = player:GetMouse()
local character = player.Character or player.CharacterAdded:Wait()
local humanoid  = character:WaitForChild("Humanoid")
local hrp       = character:WaitForChild("HumanoidRootPart")
local camera    = workspace.CurrentCamera

-- ── STATE ─────────────────────────────────────────────────────────────────────
local isDiving      = false
local currentDepth  = 0
local currentZone   = 1
local resources     = {
	Oxygen   = GameConfig.PlayerDefaults.MaxOxygen,
	MaxOxygen = GameConfig.PlayerDefaults.MaxOxygen,
}

-- ── UNDERWATER VISUALS ────────────────────────────────────────────────────────

local lighting = game:GetService("Lighting")
local colorCorrection = lighting:FindFirstChildOfClass("ColorCorrectionEffect")
	or Instance.new("ColorCorrectionEffect", lighting)
local blur = lighting:FindFirstChildOfClass("BlurEffect")
	or Instance.new("BlurEffect", lighting)

local function applyZoneVisuals(zoneIndex)
	local zone = GameConfig.Zones[zoneIndex]
	if not zone then return end

	TweenService:Create(colorCorrection, TweenInfo.new(2), {
		TintColor = zone.ambientLight,
		Brightness = -0.1 * (zoneIndex - 1),
	}):Play()

	lighting.FogEnd   = zone.fogEnd
	lighting.FogColor = zone.color
end

local function setUnderwaterFX(underwater)
	if underwater then
		TweenService:Create(blur, TweenInfo.new(0.5), { Size = 4 }):Play()
	else
		TweenService:Create(blur, TweenInfo.new(0.5), { Size = 0 }):Play()
		-- Reset to surface visuals
		TweenService:Create(colorCorrection, TweenInfo.new(1), {
			TintColor  = Color3.new(1, 1, 1),
			Brightness = 0,
		}):Play()
		lighting.FogEnd   = 1000
		lighting.FogColor = Color3.fromRGB(180, 210, 255)
	end
end

-- ── DIVING MECHANICS ──────────────────────────────────────────────────────────

local function enterWater()
	if isDiving then return end
	isDiving = true
	humanoid.WalkSpeed  = GameConfig.Diving.SwimSpeed
	humanoid.JumpPower  = 0  -- no jumping underwater
	setUnderwaterFX(true)
	Remotes.Get("PlayerDiving"):FireServer(true)
end

local function exitWater()
	if not isDiving then return end
	isDiving = false
	humanoid.WalkSpeed = 16  -- default roblox walk speed
	humanoid.JumpPower = 50
	setUnderwaterFX(false)
	Remotes.Get("PlayerDiving"):FireServer(false)
	currentZone = 1
	applyZoneVisuals(1)
end

-- ── MANUAL VERTICAL MOVEMENT (Space = up, Shift = down while diving) ─────────

UserInputService.InputBegan:Connect(function(input, processed)
	if processed then return end
	if not isDiving then return end

	if input.KeyCode == Enum.KeyCode.Space then
		-- Swim up (LinearVelocity replaces deprecated BodyVelocity)
		local lv = hrp:FindFirstChild("DiveVelocity") or Instance.new("LinearVelocity", hrp)
		lv.Name            = "DiveVelocity"
		lv.VectorVelocity  = Vector3.new(0, GameConfig.Diving.AscentSpeed, 0)
		lv.MaxForce        = 1e5
		lv.RelativeTo      = Enum.ActuatorRelativeTo.World
		game:GetService("Debris"):AddItem(lv, 0.1)
	end
end)

UserInputService.InputBegan:Connect(function(input, processed)
	if processed then return end
	if not isDiving then return end

	if input.KeyCode == Enum.KeyCode.LeftShift then
		-- Swim down
		local lv = Instance.new("LinearVelocity", hrp)
		lv.Name            = "DiveVelocity"
		lv.VectorVelocity  = Vector3.new(0, -GameConfig.Diving.DescentSpeed, 0)
		lv.MaxForce        = 1e5
		lv.RelativeTo      = Enum.ActuatorRelativeTo.World
		game:GetService("Debris"):AddItem(lv, 0.1)
	end
end)

-- ── DEPTH + ZONE TRACKING ────────────────────────────────────────────────────

RunService.Heartbeat:Connect(function()
	if not character or not hrp then return end

	local yPos   = hrp.Position.Y
	local depth  = math.max(0, -yPos)  -- depth in studs (1 stud ≈ 1 metre here)
	currentDepth = depth

	-- Detect water entry/exit (water plane at Y = 0)
	if yPos < 0 and not isDiving then
		enterWater()
	elseif yPos >= GameConfig.Diving.SurfaceDepth and isDiving then
		exitWater()
	end

	-- Zone detection while diving
	if isDiving then
		local newZone = 1
		for i, zone in ipairs(GameConfig.Zones) do
			if depth >= zone.minDepth and depth < zone.maxDepth then
				newZone = i
				break
			end
		end
		if newZone ~= currentZone then
			currentZone = newZone
			applyZoneVisuals(newZone)
		end
	end

	-- Push depth to server every ~1s (throttled by server)
	-- (server handles pressure/oxygen drain, client just tracks display)
end)

-- ── RESOURCE UPDATES FROM SERVER ─────────────────────────────────────────────

Remotes.Get("ResourceUpdate").OnClientEvent:Connect(function(res)
	resources.Oxygen    = res.Oxygen    or resources.Oxygen
	resources.MaxOxygen = GameConfig.PlayerDefaults.MaxOxygen

	-- Fire a BindableEvent so HUD script can pick it up
	-- (avoids tight coupling between scripts)
	local hud = player.PlayerGui:FindFirstChild("HUD")
	if hud then
		local updateEvent = hud:FindFirstChild("ResourceUpdateBind")
		if updateEvent then
			updateEvent:Fire(res)
		end
	end
end)

-- ── DESKTOP CLICK TO MINE / SHOOT ───────────────────────────────────────────

local shootCooldown = 0

mouse.Button1Down:Connect(function()
	if _G.BuildingClient and _G.BuildingClient.IsInBuildMode and _G.BuildingClient.IsInBuildMode() then return end
	local target = mouse.Target
	if not target then return end
	if not hrp then return end
	local dist = (target.Position - hrp.Position).Magnitude

	-- Shoot creature
	local cid = target:GetAttribute("CreatureId")
	if cid then
		local now = tick()
		if now - shootCooldown < 0.4 then return end
		shootCooldown = now
		if dist > 80 then return end
		Remotes.Get("ShootCreature"):FireServer(cid, 15)
		-- Floating damage number client-side
		local lbl = Instance.new("TextLabel")
		lbl.Size  = UDim2.new(0, 60, 0, 22)
		lbl.BackgroundTransparency = 1
		lbl.Text  = "-15"
		lbl.TextColor3 = Color3.fromRGB(255, 80, 60)
		lbl.TextStrokeColor3 = Color3.new(0,0,0)
		lbl.TextStrokeTransparency = 0.3
		lbl.Font  = Enum.Font.GothamBold
		lbl.TextScaled = true
		lbl.ZIndex = 25
		local absPos = mouse.X
		local absPosy = mouse.Y
		lbl.Position = UDim2.new(0, absPos - 30, 0, absPosy - 10)
		local hud = player.PlayerGui:FindFirstChild("HUD")
		lbl.Parent = hud or player.PlayerGui
		TweenService:Create(lbl, TweenInfo.new(0.9, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
			Position = UDim2.new(0, absPos - 30, 0, absPosy - 55),
			TextTransparency = 1,
			TextStrokeTransparency = 1,
		}):Play()
		game:GetService("Debris"):AddItem(lbl, 1)
		return
	end

	-- Mine mineral node
	if not target:GetAttribute("NodeId") then return end
	if dist > 20 then return end
	Remotes.Get("MineNode"):FireServer(target)
end)

-- ── CHARACTER RESPAWN ─────────────────────────────────────────────────────────

player.CharacterAdded:Connect(function(newChar)
	character = newChar
	humanoid  = newChar:WaitForChild("Humanoid")
	hrp       = newChar:WaitForChild("HumanoidRootPart")
	isDiving  = false
	currentZone = 1
end)

-- ── NOTIFY CLIENT ON ZONE CHANGE (for HUD zone label) ─────────────────────────

Remotes.Get("ZoneUnlocked").OnClientEvent:Connect(function(zoneIndex)
	local zone = GameConfig.Zones[zoneIndex]
	if zone then
		-- HUD script shows the unlock notification
		local hud = player.PlayerGui:FindFirstChild("HUD")
		if hud then
			local notifBind = hud:FindFirstChild("NotifBind")
			if notifBind then
				notifBind:Fire("Zone Unlocked!", zone.name .. " is now accessible!", "success")
			end
		end
	end
end)
