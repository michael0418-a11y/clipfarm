-- LoadingScreen.client.lua
-- Animated loading screen shown while the game loads assets
-- Place in StarterGui as a LocalScript inside a ScreenGui named "LoadingScreen"
-- Set ScreenGui.DisplayOrder = 100 so it appears on top of everything

local Players           = game:GetService("Players")
local ContentProvider   = game:GetService("ContentProvider")
local TweenService      = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local gui    = script.Parent

-- ── BACKGROUND ────────────────────────────────────────────────────────────────

local bg            = Instance.new("Frame", gui)
bg.Name             = "Background"
bg.Size             = UDim2.new(1, 0, 1, 0)
bg.BackgroundColor3 = Color3.fromRGB(2, 8, 30)
bg.ZIndex           = 100

-- Animated gradient overlay
local gradient       = Instance.new("UIGradient", bg)
gradient.Color       = ColorSequence.new({
	ColorSequenceKeypoint.new(0, Color3.fromRGB(0, 20, 80)),
	ColorSequenceKeypoint.new(0.5, Color3.fromRGB(0, 60, 120)),
	ColorSequenceKeypoint.new(1, Color3.fromRGB(0, 10, 50)),
})
gradient.Rotation    = 135

-- ── TITLE ────────────────────────────────────────────────────────────────────

local titleLabel     = Instance.new("TextLabel", bg)
titleLabel.Size      = UDim2.new(0.7, 0, 0.15, 0)
titleLabel.Position  = UDim2.new(0.15, 0, 0.22, 0)
titleLabel.BackgroundTransparency = 1
titleLabel.Text      = "UNDERWATER TYCOON"
titleLabel.TextColor3 = Color3.fromRGB(100, 220, 255)
titleLabel.TextScaled = true
titleLabel.Font       = Enum.Font.GothamBold
titleLabel.ZIndex     = 101
titleLabel.TextTransparency = 1

-- Subtitle
local subLabel       = Instance.new("TextLabel", bg)
subLabel.Size        = UDim2.new(0.5, 0, 0.06, 0)
subLabel.Position    = UDim2.new(0.25, 0, 0.37, 0)
subLabel.BackgroundTransparency = 1
subLabel.Text        = "Build. Dive. Survive."
subLabel.TextColor3  = Color3.fromRGB(150, 200, 255)
subLabel.TextScaled  = true
subLabel.Font        = Enum.Font.Gotham
subLabel.ZIndex      = 101
subLabel.TextTransparency = 1

-- ── WAVE ANIMATION DOTS ───────────────────────────────────────────────────────

local waveContainer  = Instance.new("Frame", bg)
waveContainer.Size   = UDim2.new(0, 80, 0, 30)
waveContainer.Position = UDim2.new(0.5, -40, 0.6, 0)
waveContainer.BackgroundTransparency = 1
waveContainer.ZIndex = 101

local dots = {}
for i = 1, 5 do
	local dot        = Instance.new("Frame", waveContainer)
	dot.Size         = UDim2.new(0, 12, 0, 12)
	dot.Position     = UDim2.new(0, (i - 1) * 17, 0, 9)
	dot.BackgroundColor3 = Color3.fromRGB(0, 180, 255)
	dot.BorderSizePixel = 0
	dot.ZIndex       = 102
	local c          = Instance.new("UICorner", dot)
	c.CornerRadius   = UDim.new(1, 0)
	dots[i]          = dot
end

-- ── PROGRESS BAR ─────────────────────────────────────────────────────────────

local barBg          = Instance.new("Frame", bg)
barBg.Size           = UDim2.new(0.4, 0, 0, 6)
barBg.Position       = UDim2.new(0.3, 0, 0.7, 0)
barBg.BackgroundColor3 = Color3.fromRGB(20, 40, 80)
barBg.BorderSizePixel = 0
barBg.ZIndex         = 101
local barCorner      = Instance.new("UICorner", barBg)
barCorner.CornerRadius = UDim.new(1, 0)

local barFill        = Instance.new("Frame", barBg)
barFill.Size         = UDim2.new(0, 0, 1, 0)
barFill.BackgroundColor3 = Color3.fromRGB(0, 180, 255)
barFill.BorderSizePixel = 0
barFill.ZIndex       = 102
local fillCorner     = Instance.new("UICorner", barFill)
fillCorner.CornerRadius = UDim.new(1, 0)

local progressLabel  = Instance.new("TextLabel", bg)
progressLabel.Size   = UDim2.new(0.4, 0, 0, 24)
progressLabel.Position = UDim2.new(0.3, 0, 0.72, 0)
progressLabel.BackgroundTransparency = 1
progressLabel.Text   = "Loading ocean world..."
progressLabel.TextColor3 = Color3.fromRGB(120, 180, 220)
progressLabel.TextScaled = true
progressLabel.Font   = Enum.Font.Gotham
progressLabel.ZIndex = 101

-- ── ANIMATIONS ────────────────────────────────────────────────────────────────

-- Fade in title
TweenService:Create(titleLabel, TweenInfo.new(1.2, Enum.EasingStyle.Quad), {
	TextTransparency = 0,
}):Play()
TweenService:Create(subLabel, TweenInfo.new(1.5, Enum.EasingStyle.Quad), {
	TextTransparency = 0,
}):Play()

-- Wave dot animation
local function animateDots()
	while gui.Enabled do
		for i, dot in ipairs(dots) do
			task.delay((i - 1) * 0.12, function()
				TweenService:Create(dot, TweenInfo.new(0.3, Enum.EasingStyle.Sine), {
					Position = UDim2.new(0, (i - 1) * 17, 0, -2),
				}):Play()
				task.delay(0.3, function()
					TweenService:Create(dot, TweenInfo.new(0.3, Enum.EasingStyle.Sine), {
						Position = UDim2.new(0, (i - 1) * 17, 0, 9),
					}):Play()
				end)
			end)
		end
		task.wait(0.8)
	end
end
task.spawn(animateDots)

-- ── LOAD PROGRESS ────────────────────────────────────────────────────────────

local loadMessages = {
	"Filling the ocean...",
	"Spawning sea creatures...",
	"Growing coral reefs...",
	"Setting up your base...",
	"Calibrating pressure systems...",
	"Ready to dive!",
}

local function setProgress(pct, message)
	TweenService:Create(barFill, TweenInfo.new(0.4), {
		Size = UDim2.new(pct, 0, 1, 0),
	}):Play()
	progressLabel.Text = message
end

-- Simulate loading steps while waiting for game to be ready
task.spawn(function()
	for i, msg in ipairs(loadMessages) do
		local pct = i / #loadMessages
		setProgress(pct, msg)
		task.wait(0.6)
	end
end)

-- Wait for RemoteEvents to exist (signals server is ready)
ReplicatedStorage:WaitForChild("Remotes", 30)

-- Small extra delay for immersion
task.wait(0.5)

-- ── FADE OUT ─────────────────────────────────────────────────────────────────

TweenService:Create(bg, TweenInfo.new(1, Enum.EasingStyle.Quad), {
	BackgroundTransparency = 1,
}):Play()
TweenService:Create(titleLabel, TweenInfo.new(0.8), { TextTransparency = 1 }):Play()
TweenService:Create(subLabel,   TweenInfo.new(0.8), { TextTransparency = 1 }):Play()
TweenService:Create(barBg,      TweenInfo.new(0.8), { BackgroundTransparency = 1 }):Play()
TweenService:Create(barFill,    TweenInfo.new(0.8), { BackgroundTransparency = 1 }):Play()
TweenService:Create(progressLabel, TweenInfo.new(0.8), { TextTransparency = 1 }):Play()

for _, dot in ipairs(dots) do
	TweenService:Create(dot, TweenInfo.new(0.8), { BackgroundTransparency = 1 }):Play()
end

task.wait(1.1)
gui.Enabled = false
