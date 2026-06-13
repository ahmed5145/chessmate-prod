import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import ProfileCoachSettings from '../profile/ProfileCoachSettings';
import { getUserProfile, updateUserProfile } from '../../services/apiRequests';

jest.mock("react-hot-toast");
jest.mock("../../services/apiRequests");

const mockProfile = {
  username: "coachuser",
  email: "coach@example.com",
  rating: 1500,
  preferences: {
    emailNotifications: true,
    coach_persona: "encouraging",
    wants_reactivation_email: false,
  },
};

describe("CoachPersonaSettings", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getUserProfile.mockResolvedValue(mockProfile);
  });

  it("renders coach tone toggle and saves direct persona", async () => {
    updateUserProfile.mockResolvedValue({
      ...mockProfile,
      preferences: { ...mockProfile.preferences, coach_persona: "direct" },
    });

    render(
      <BrowserRouter>
        <ProfileCoachSettings isDarkMode={false} />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole("group", { name: /coach tone/i })).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /save preferences/i })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: /^direct$/i }));

    expect(screen.getByRole("button", { name: /save preferences/i })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: /save preferences/i }));

    await waitFor(() => {
      expect(updateUserProfile).toHaveBeenCalledWith({
        preferences: expect.objectContaining({ coach_persona: "direct" }),
      });
    });
  });
});
