import React from "react";
import { useAuth0 } from "@auth0/auth0-react";

const Profile = () => {
    const { user, isAuthenticated, isLoading } = useAuth0();

    if (isLoading) {
        return <div>Loading ...</div>;
    }

    return (
        isAuthenticated && user && (
            <div className="flex items-center gap-4 p-4 bg-gray-100 rounded-lg shadow">
                {user.picture && <img src={user.picture} alt={user.name} className="w-12 h-12 rounded-full" />}
                <div>
                    <h2 className="text-lg font-semibold">{user.name}</h2>
                    <p className="text-gray-600">{user.email}</p>
                </div>
            </div>
        )
    );
};

export default Profile;
