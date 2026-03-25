-- BuildingClient.client.lua
-- Client-side building placement: ghost preview, snapping, confirmation
-- Place in StarterPlayer/StarterPlayerScripts as a LocalScript

local Players           = game:GetService("Players")
local UserInputService  = game:GetService("UserInputService")
local RunService        = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local GameConfig  = require(ReplicatedStorage:WaitForChild("GameConfig"))
local ModuleData  = require(ReplicatedStorage:WaitForChild("Modules"):WaitForChild("ModuleData"))
local Remotes     = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local player    = Players.LocalPlayer
local camera    = workspace.CurrentCamera
local mouse     = player:GetMouse()

-- ── STATE ─────────────────────────────────────────────────────────────────────
local buildMode        = false
local selectedModuleId = nil
local ghostPart        = nil       -- transparent preview part
local rotation         = 0         -- Y rotation in degrees
local GRID_SIZE        = 4         -- snap to 4 stud grid

-- ── GHOST PART ────────────────────────────────────────────────────────────────

local function destroyGhost()
	if ghostPart then
		ghostPart:Destroy()
		ghostPart = nil
	end
end

local function createGhost(modDef)
	destroyGhost()
	local part            = Instance.new("Part")
	part.Name             = "GhostModule"
	part.Size             = modDef.size
	part.Color            = modDef.color
	part.Transparency     = 0.5
	part.Anchored         = true
	part.CanCollide       = false
	part.CastShadow       = false
	part.Material         = Enum.Material.SmoothPlastic
	part.Parent           = workspace

	-- Green selection box
	local selBox          = Instance.new("SelectionBox", part)
	selBox.Adornee        = part
	selBox.Color3         = Color3.fromRGB(0, 255, 100)
	selBox.LineThickness  = 0.05

	ghostPart = part
	return part
end

-- ── SNAP TO GRID ──────────────────────────────────────────────────────────────

local function snapToGrid(pos)
	return Vector3.new(
		math.round(pos.X / GRID_SIZE) * GRID_SIZE,
		math.round(pos.Y / GRID_SIZE) * GRID_SIZE,
		math.round(pos.Z / GRID_SIZE) * GRID_SIZE
	)
end

-- ── RAYCAST FOR PLACEMENT ─────────────────────────────────────────────────────

local rayParams = RaycastParams.new()
rayParams.FilterType = Enum.RaycastFilterType.Exclude

local function getPlacementCFrame()
	local character = player.Character
	if character then
		rayParams.FilterDescendantsInstances = { character, ghostPart }
	end

	local unitRay  = camera:ScreenPointToRay(mouse.X, mouse.Y)
	local result   = workspace:Raycast(unitRay.Origin, unitRay.Direction * 500, rayParams)

	if result then
		local snapped = snapToGrid(result.Position)
		return CFrame.new(snapped) * CFrame.Angles(0, math.rad(rotation), 0), true
	end
	return nil, false
end

-- ── BUILD MODE LOOP ───────────────────────────────────────────────────────────

RunService.RenderStepped:Connect(function()
	if not buildMode or not ghostPart then return end
	local cf, hit = getPlacementCFrame()
	if hit then
		ghostPart.CFrame = cf
		-- Green if valid, red if blocked
		local selBox = ghostPart:FindFirstChildOfClass("SelectionBox")
		if selBox then
			selBox.Color3 = Color3.fromRGB(0, 255, 100)
		end
	end
end)

-- ── INPUT: ROTATE ─────────────────────────────────────────────────────────────

UserInputService.InputBegan:Connect(function(input, processed)
	if processed then return end
	if not buildMode then return end

	if input.KeyCode == Enum.KeyCode.R then
		rotation = (rotation + 90) % 360
	elseif input.KeyCode == Enum.KeyCode.Escape then
		BuildingClient.ExitBuildMode()
	end
end)

-- ── INPUT: PLACE ──────────────────────────────────────────────────────────────

mouse.Button1Down:Connect(function()
	if not buildMode or not selectedModuleId then return end

	local cf, hit = getPlacementCFrame()
	if not hit then return end

	local pos = cf.Position
	Remotes.Get("PlaceModule"):FireServer(
		selectedModuleId,
		{ pos.X, pos.Y, pos.Z },
		rotation
	)
	-- Stay in build mode so player can place multiple of the same module
end)

-- ── BUILD MODE: ENTER / EXIT ──────────────────────────────────────────────────

local BuildingClient = {}

function BuildingClient.EnterBuildMode(moduleId)
	local modDef = ModuleData.Get(moduleId)
	if not modDef then return end

	buildMode        = true
	selectedModuleId = moduleId
	rotation         = 0
	createGhost(modDef)
end

function BuildingClient.ExitBuildMode()
	buildMode        = false
	selectedModuleId = nil
	rotation         = 0
	destroyGhost()
end

-- ── RESPONSES FROM SERVER ─────────────────────────────────────────────────────

Remotes.Get("ModulePlaced").OnClientEvent:Connect(function(entry)
	-- The server has confirmed placement; nothing extra needed client-side
	-- (The world part is already built server-side and replicated)
end)

Remotes.Get("ResourceError").OnClientEvent:Connect(function(msg)
	-- Show error in HUD
	local hud = player.PlayerGui:FindFirstChild("HUD")
	if hud then
		local notifBind = hud:FindFirstChild("NotifBind")
		if notifBind then
			notifBind:Fire("Error", msg, "danger")
		end
	end
end)

-- Expose to GUI scripts via _G (simple coupling for Roblox)
_G.BuildingClient = BuildingClient

return BuildingClient
