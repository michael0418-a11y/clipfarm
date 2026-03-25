-- ModeSelectGui.client.lua
-- Solo vs Multiplayer mode selection screen shown on game start
-- Place in StarterGui as a LocalScript inside a ScreenGui named "ModeSelectGui"

local Players           = game:GetService("Players")
local TweenService      = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage:WaitForChild("RemoteEvents"))
local player  = Players.LocalPlayer
local gui     = script.Parent  -- the ScreenGui

-- ── BUILD UI ──────────────────────────────────────────────────────────────────

-- Dim background
local bg            = Instance.new("Frame", gui)
bg.Name             = "Background"
bg.Size             = UDim2.new(1, 0, 1, 0)
bg.BackgroundColor3 = Color3.fromRGB(5, 15, 40)
bg.BackgroundTransparency = 0
bg.ZIndex           = 10

-- Title
local title         = Instance.new("TextLabel", bg)
title.Name          = "Title"
title.Size          = UDim2.new(0.6, 0, 0.15, 0)
title.Position      = UDim2.new(0.2, 0, 0.1, 0)
title.BackgroundTransparency = 1
title.Text          = "🌊 UNDERWATER TYCOON"
title.TextColor3    = Color3.fromRGB(100, 220, 255)
title.TextScaled    = true
title.Font          = Enum.Font.GothamBold
title.ZIndex        = 11

-- Subtitle
local sub           = Instance.new("TextLabel", bg)
sub.Name            = "Subtitle"
sub.Size            = UDim2.new(0.5, 0, 0.06, 0)
sub.Position        = UDim2.new(0.25, 0, 0.24, 0)
sub.BackgroundTransparency = 1
sub.Text            = "Choose your adventure"
sub.TextColor3      = Color3.fromRGB(180, 200, 220)
sub.TextScaled      = true
sub.Font            = Enum.Font.Gotham
sub.ZIndex          = 11

-- ── MODE CARD BUILDER ─────────────────────────────────────────────────────────

local function makeCard(name, xPos, icon, descLines, color)
	local card           = Instance.new("Frame", bg)
	card.Name            = name .. "Card"
	card.Size            = UDim2.new(0.28, 0, 0.45, 0)
	card.Position        = UDim2.new(xPos, 0, 0.33, 0)
	card.BackgroundColor3 = Color3.fromRGB(10, 30, 70)
	card.BorderSizePixel = 0
	card.ZIndex          = 11

	local corner         = Instance.new("UICorner", card)
	corner.CornerRadius  = UDim.new(0, 12)

	local stroke         = Instance.new("UIStroke", card)
	stroke.Color         = color
	stroke.Thickness     = 2

	-- Icon
	local iconLabel      = Instance.new("TextLabel", card)
	iconLabel.Size       = UDim2.new(1, 0, 0.25, 0)
	iconLabel.Position   = UDim2.new(0, 0, 0.05, 0)
	iconLabel.BackgroundTransparency = 1
	iconLabel.Text       = icon
	iconLabel.TextScaled = true
	iconLabel.ZIndex     = 12

	-- Mode name
	local nameLabel      = Instance.new("TextLabel", card)
	nameLabel.Size       = UDim2.new(1, 0, 0.15, 0)
	nameLabel.Position   = UDim2.new(0, 0, 0.3, 0)
	nameLabel.BackgroundTransparency = 1
	nameLabel.Text       = name
	nameLabel.TextColor3 = color
	nameLabel.TextScaled = true
	nameLabel.Font       = Enum.Font.GothamBold
	nameLabel.ZIndex     = 12

	-- Description lines
	local desc           = Instance.new("TextLabel", card)
	desc.Size            = UDim2.new(0.85, 0, 0.3, 0)
	desc.Position        = UDim2.new(0.075, 0, 0.46, 0)
	desc.BackgroundTransparency = 1
	desc.Text            = descLines
	desc.TextColor3      = Color3.fromRGB(180, 200, 220)
	desc.TextScaled      = true
	desc.TextWrapped     = true
	desc.Font            = Enum.Font.Gotham
	desc.ZIndex          = 12

	-- Select button
	local btn            = Instance.new("TextButton", card)
	btn.Name             = "SelectBtn"
	btn.Size             = UDim2.new(0.7, 0, 0.14, 0)
	btn.Position         = UDim2.new(0.15, 0, 0.82, 0)
	btn.BackgroundColor3 = color
	btn.Text             = "SELECT"
	btn.TextColor3       = Color3.new(1, 1, 1)
	btn.TextScaled       = true
	btn.Font             = Enum.Font.GothamBold
	btn.ZIndex           = 12

	local btnCorner      = Instance.new("UICorner", btn)
	btnCorner.CornerRadius = UDim.new(0, 8)

	-- Hover effect
	btn.MouseEnter:Connect(function()
		TweenService:Create(card, TweenInfo.new(0.15), {
			BackgroundColor3 = Color3.fromRGB(15, 45, 100),
		}):Play()
	end)
	btn.MouseLeave:Connect(function()
		TweenService:Create(card, TweenInfo.new(0.15), {
			BackgroundColor3 = Color3.fromRGB(10, 30, 70),
		}):Play()
	end)

	return btn
end

local soloBtn = makeCard(
	"SOLO",
	0.1,
	"🤿",
	"Your own private base.\nPeaceful or private PvP.\nProgress at your own pace.",
	Color3.fromRGB(0, 180, 255)
)

local multiBtn = makeCard(
	"MULTIPLAYER",
	0.62,
	"👥",
	"Shared server.\nCo-op build OR raid others.\nOpt-in PvP base raiding.",
	Color3.fromRGB(80, 255, 150)
)

-- ── SELECTION HANDLER ─────────────────────────────────────────────────────────

local function selectMode(mode)
	Remotes.Get("SelectMode"):FireServer(mode)
end

soloBtn.Activated:Connect(function()  selectMode("Solo")        end)
multiBtn.Activated:Connect(function() selectMode("Multiplayer") end)

-- ── CLOSE ON CONFIRMATION ─────────────────────────────────────────────────────

Remotes.Get("ModeConfirmed").OnClientEvent:Connect(function(mode)
	TweenService:Create(bg, TweenInfo.new(0.8), {
		BackgroundTransparency = 1,
	}):Play()
	task.delay(0.85, function()
		gui.Enabled = false
	end)
end)
