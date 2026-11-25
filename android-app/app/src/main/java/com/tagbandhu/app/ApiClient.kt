
package com.tagbandhu.app

import retrofit2.Call
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PUT

data class LoginRequest(
    val email: String,
    val password: String
)

data class ApiUser(
    val id: Int,
    val name: String,
    val email: String,
    val phone: String = ""
)

data class LoginResponse(
    val success: Boolean,
    val message: String,
    val token: String? = null,
    val user: ApiUser? = null
)

data class ProfileUpdateRequest(
    val name: String,
    val phone: String
)

data class ProfileResponse(
    val success: Boolean,
    val message: String? = null,
    val user: ApiUser? = null
)

data class TagItem(
    val id: Int,
    val tag_code: String,
    val tag_type: String,
    val is_active: Boolean,
    val activated_at: String? = null
)

data class TagsResponse(
    val success: Boolean,
    val tags: List<TagItem>
)

interface TagbandhuApi {

    @POST("api/login")
    fun login(
        @Body request: LoginRequest
    ): Call<LoginResponse>

    @GET("api/my-tags")
    fun getMyTags(
        @Header("Authorization") token: String
    ): Call<TagsResponse>

    @GET("api/profile")
    fun getProfile(
        @Header("Authorization") token: String
    ): Call<ProfileResponse>

    @PUT("api/profile")
    fun updateProfile(
        @Header("Authorization") token: String,
        @Body request: ProfileUpdateRequest
    ): Call<ProfileResponse>
}

object ApiClient {

    private const val BASE_URL =
        "http://10.75.90.87:5000/"

    val service: TagbandhuApi by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(
                GsonConverterFactory.create()
            )
            .build()
            .create(TagbandhuApi::class.java)
    }
}
