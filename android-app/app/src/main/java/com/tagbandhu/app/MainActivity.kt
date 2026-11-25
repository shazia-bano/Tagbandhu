package com.tagbandhu.app

import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Checkbox
import androidx.compose.material3.TextButton
import androidx.compose.ui.text.input.PasswordVisualTransformation
import retrofit2.Call
import retrofit2.Callback
import androidx.compose.runtime.LaunchedEffect
import retrofit2.Response
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import android.app.Activity
import android.widget.Toast
import androidx.compose.ui.platform.LocalContext
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Checkbox
import androidx.compose.material3.TextButton
import androidx.compose.ui.text.input.KeyboardType
private val Forest = Color(0xFF173D35)
private val Mint = Color(0xFFDDF3D0)
private val Cream = Color(0xFFF7F8F3)
private val Muted = Color(0xFF68756E)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                TagbandhuApp()
            }
        }
    }
}


@Composable
fun TagbandhuApp() {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var token by remember { mutableStateOf<String?>(null) }
    var userName by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }

    var screen by remember { mutableStateOf("login") }

    var registerName by remember { mutableStateOf("") }
    var registerPhone by remember { mutableStateOf("") }
    var registerEmail by remember { mutableStateOf("") }
    var registerPassword by remember { mutableStateOf("") }
    var consent by remember { mutableStateOf(false) }
    var otp by remember { mutableStateOf("") }

    if (token != null) {
        TagbandhuDashboard(
            token = token!!,
            loggedInName = userName
        )
        return
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Cream
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                text = "🏷️ Tagbandhu",
                fontSize = 30.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Forest
            )

            Spacer(Modifier.height(8.dp))

            when (screen) {

                "login" -> {
                    Text(
                        text = "Login to access your real tags",
                        color = Muted
                    )

                    Spacer(Modifier.height(28.dp))

                    OutlinedTextField(
                        value = email,
                        onValueChange = { email = it },
                        label = { Text("Email address") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    Spacer(Modifier.height(12.dp))

                    OutlinedTextField(
                        value = password,
                        onValueChange = { password = it },
                        label = { Text("Password") },
                        visualTransformation =
                            PasswordVisualTransformation(),
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    Spacer(Modifier.height(18.dp))

                    Button(
                        onClick = {
                            if (email.isBlank() || password.isBlank()) {
                                message = "Email aur password enter karo."
                                return@Button
                            }

                            loading = true
                            message = ""

                            ApiClient.service.login(
                                LoginRequest(
                                    email = email.trim(),
                                    password = password
                                )
                            ).enqueue(object : Callback<LoginResponse> {

                                override fun onResponse(
                                    call: Call<LoginResponse>,
                                    response: Response<LoginResponse>
                                ) {
                                    loading = false
                                    val result = response.body()

                                    if (
                                        response.isSuccessful &&
                                        result?.success == true &&
                                        !result.token.isNullOrBlank()
                                    ) {
                                        userName = result.user?.name ?: ""
                                        token = result.token
                                    } else {
                                        message = result?.message
                                            ?: "Login failed. Check your details or verify your email."
                                    }
                                }

                                override fun onFailure(
                                    call: Call<LoginResponse>,
                                    t: Throwable
                                ) {
                                    loading = false
                                    message = "Server connection failed: " +
                                            (t.message ?: "Try again")
                                }
                            })
                        },
                        enabled = !loading,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(if (loading) "Logging in..." else "Login")
                    }

                    TextButton(
                        onClick = {
                            screen = "register"
                            message = ""
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("New to Tagbandhu? Create Account")
                    }
                }

                "register" -> {
                    Text(
                        text = "Create your account",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = Forest
                    )

                    Spacer(Modifier.height(8.dp))

                    Text(
                        text = "Enter your details to get started.",
                        color = Muted
                    )

                    Spacer(Modifier.height(20.dp))

                    OutlinedTextField(
                        value = registerName,
                        onValueChange = { registerName = it },
                        label = { Text("Full name") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    Spacer(Modifier.height(12.dp))

                    OutlinedTextField(
                        value = registerPhone,
                        onValueChange = { registerPhone = it },
                        label = { Text("Phone number") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Phone
                        )
                    )

                    Spacer(Modifier.height(12.dp))

                    OutlinedTextField(
                        value = registerEmail,
                        onValueChange = { registerEmail = it },
                        label = { Text("Email address") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Email
                        )
                    )

                    Spacer(Modifier.height(12.dp))

                    OutlinedTextField(
                        value = registerPassword,
                        onValueChange = { registerPassword = it },
                        label = { Text("Password") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        visualTransformation =
                            PasswordVisualTransformation()
                    )

                    Spacer(Modifier.height(8.dp))

                    Row(
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Checkbox(
                            checked = consent,
                            onCheckedChange = { consent = it }
                        )

                        Text(
                            text = "I agree to the terms and privacy policy."
                        )
                    }

                    Spacer(Modifier.height(12.dp))

                    Button(
                        onClick = {
                            if (
                                registerName.isBlank() ||
                                registerPhone.isBlank() ||
                                registerEmail.isBlank() ||
                                registerPassword.isBlank()
                            ) {
                                message = "Saari details fill karo."
                                return@Button
                            }

                            if (!consent) {
                                message = "Please accept the consent."
                                return@Button
                            }

                            loading = true
                            message = ""

                            ApiClient.service.register(
                                RegisterRequest(
                                    name = registerName.trim(),
                                    phone = registerPhone.trim(),
                                    email = registerEmail.trim().lowercase(),
                                    password = registerPassword,
                                    consent = consent
                                )
                            ).enqueue(object : Callback<RegisterResponse> {

                                override fun onResponse(
                                    call: Call<RegisterResponse>,
                                    response: Response<RegisterResponse>
                                ) {
                                    loading = false
                                    val result = response.body()

                                    if (
                                        response.isSuccessful &&
                                        result?.success == true
                                    ) {
                                        email = registerEmail.trim().lowercase()
                                        otp = ""
                                        message = result.message
                                        screen = "otp"
                                    } else {
                                        message = result?.message
                                            ?: "Registration failed. Check the details or try another email."
                                    }
                                }

                                override fun onFailure(
                                    call: Call<RegisterResponse>,
                                    t: Throwable
                                ) {
                                    loading = false
                                    message = "Server connection failed: " +
                                            (t.message ?: "Try again")
                                }
                            })
                        },
                        enabled = !loading,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            if (loading) "Creating account..."
                            else "Create Account"
                        )
                    }

                    TextButton(
                        onClick = {
                            screen = "login"
                            message = ""
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Already registered? Login")
                    }
                }

                "otp" -> {
                    Text(
                        text = "Verify your email",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = Forest
                    )

                    Spacer(Modifier.height(8.dp))

                    Text(
                        text = "Enter the 6-digit OTP sent to $email",
                        color = Muted
                    )

                    Spacer(Modifier.height(20.dp))

                    OutlinedTextField(
                        value = otp,
                        onValueChange = {
                            otp = it.filter { char -> char.isDigit() }
                                .take(6)
                        },
                        label = { Text("6-digit OTP") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Number
                        )
                    )

                    Spacer(Modifier.height(16.dp))

                    Button(
                        onClick = {
                            if (otp.length != 6) {
                                message = "6-digit OTP enter karo."
                                return@Button
                            }

                            loading = true
                            message = ""

                            ApiClient.service.verifyEmail(
                                VerifyEmailRequest(
                                    email = email.trim().lowercase(),
                                    otp = otp
                                )
                            ).enqueue(object : Callback<VerifyEmailResponse> {

                                override fun onResponse(
                                    call: Call<VerifyEmailResponse>,
                                    response: Response<VerifyEmailResponse>
                                ) {
                                    loading = false
                                    val result = response.body()

                                    if (
                                        response.isSuccessful &&
                                        result?.success == true
                                    ) {
                                        screen = "login"
                                        password = ""
                                        message =
                                            "Email verified! Ab login karo."
                                    } else {
                                        message = result?.message
                                            ?: "OTP verification failed. Check the OTP and try again."
                                    }
                                }

                                override fun onFailure(
                                    call: Call<VerifyEmailResponse>,
                                    t: Throwable
                                ) {
                                    loading = false
                                    message = "Server connection failed: " +
                                            (t.message ?: "Try again")
                                }
                            })
                        },
                        enabled = !loading,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(if (loading) "Verifying..." else "Verify Email")
                    }

                    TextButton(
                        onClick = {
                            loading = true
                            message = ""

                            ApiClient.service.resendVerification(
                                ResendOtpRequest(
                                    email = email.trim().lowercase()
                                )
                            ).enqueue(object : Callback<ResendOtpResponse> {

                                override fun onResponse(
                                    call: Call<ResendOtpResponse>,
                                    response: Response<ResendOtpResponse>
                                ) {
                                    loading = false
                                    message = response.body()?.message
                                        ?: "Could not resend OTP. Please wait and try again."
                                }

                                override fun onFailure(
                                    call: Call<ResendOtpResponse>,
                                    t: Throwable
                                ) {
                                    loading = false
                                    message = "Server connection failed: " +
                                            (t.message ?: "Try again")
                                }
                            })
                        },
                        enabled = !loading,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Resend OTP")
                    }

                    TextButton(
                        onClick = {
                            screen = "login"
                            message = ""
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Back to Login")
                    }
                }
            }

            if (message.isNotBlank()) {
                Spacer(Modifier.height(12.dp))

                Text(
                    text = message,
                    color = MaterialTheme.colorScheme.error
                )
            }
        }
    }
}

@Composable
fun TagbandhuHomeScreen() {
    var searchText by remember { mutableStateOf("") }
    var selectedCategory by remember { mutableStateOf("All") }
    var selectedTab by remember { mutableStateOf("Home") }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Cream
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp)
            ) {
                Spacer(Modifier.height(22.dp))

                // Brand header
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(48.dp)
                            .background(Mint, RoundedCornerShape(16.dp)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text("🏷️", fontSize = 25.sp)
                    }

                    Spacer(Modifier.width(12.dp))

                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            "Tagbandhu",
                            fontSize = 25.sp,
                            fontWeight = FontWeight.ExtraBold,
                            color = Forest
                        )
                        Text(
                            "Your shopping companion",
                            fontSize = 12.sp,
                            color = Muted
                        )
                    }

                    Text("🛍️", fontSize = 25.sp)
                }

                Spacer(Modifier.height(28.dp))

                // Welcome banner
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Forest, RoundedCornerShape(24.dp))
                        .padding(22.dp)
                ) {
                    Text(
                        "HELLO, THERE 👋",
                        color = Mint,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(Modifier.height(10.dp))
                    Text(
                        "Find something\nwonderful.",
                        color = Color.White,
                        fontSize = 29.sp,
                        lineHeight = 35.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "Your next favourite thing is waiting.",
                        color = Color(0xFFE0EAE5),
                        fontSize = 13.sp
                    )
                    Spacer(Modifier.height(18.dp))
                    Row(
                        modifier = Modifier
                            .background(Mint, RoundedCornerShape(12.dp))
                            .clickable { selectedTab = "Explore" }
                            .padding(horizontal = 17.dp, vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            "Explore now",
                            color = Forest,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(Modifier.width(8.dp))
                        Text("→", color = Forest)
                    }
                }

                Spacer(Modifier.height(25.dp))
                // Search field
                OutlinedTextField(
                    value = searchText,
                    onValueChange = { searchText = it },
                    modifier = Modifier.fillMaxWidth(),
                    placeholder = {
                        Text("Search products...", color = Muted)
                    },
                    leadingIcon = {
                        Text("🔎", fontSize = 18.sp)
                    },
                    shape = RoundedCornerShape(16.dp),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        unfocusedContainerColor = Color.White,
                        focusedContainerColor = Color.White,
                        unfocusedBorderColor = Color(0xFFE3E8E1),
                        focusedBorderColor = Forest
                    )
                )

                Spacer(Modifier.height(25.dp))

                // Categories
                Text(
                    "Shop by category",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = Forest
                )
                Spacer(Modifier.height(5.dp))
                Text(
                    "A little something for everyone",
                    color = Muted,
                    fontSize = 13.sp
                )
                Spacer(Modifier.height(15.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    CategoryChip(
                        name = "All",
                        emoji = "✨",
                        selected = selectedCategory == "All",
                        modifier = Modifier.weight(1f)
                    ) { selectedCategory = "All" }

                    CategoryChip(
                        name = "Fashion",
                        emoji = "👕",
                        selected = selectedCategory == "Fashion",
                        modifier = Modifier.weight(1f)
                    ) { selectedCategory = "Fashion" }

                    CategoryChip(
                        name = "Tech",
                        emoji = "🎧",
                        selected = selectedCategory == "Tech",
                        modifier = Modifier.weight(1f)
                    ) { selectedCategory = "Tech" }
                }

                Spacer(Modifier.height(27.dp))

                // Featured products
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        "Featured picks",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = Forest,
                        modifier = Modifier.weight(1f)
                    )
                    Text(
                        "JUST FOR YOU",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = Muted
                    )
                }

                Spacer(Modifier.height(15.dp))

                val products = listOf(
                    Triple("🎧", "Wireless Headphones", "₹1,499"),
                    Triple("🎒", "Everyday Backpack", "₹899"),
                    Triple("⌚", "Smart Watch", "₹2,499"),
                    Triple("👟", "Everyday Sneakers", "₹1,799")
                ).filter {
                    it.second.contains(searchText, ignoreCase = true) ||
                            searchText.isBlank()
                }

                products.chunked(2).forEach { pair ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        pair.forEach { product ->
                            ProductCard(
                                emoji = product.first,
                                name = product.second,
                                price = product.third,
                                modifier = Modifier.weight(1f)
                            )
                        }
                        if (pair.size == 1) {
                            Spacer(Modifier.weight(1f))
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                }

                if (products.isEmpty()) {
                    Text(
                        "No matching demo products found.",
                        color = Muted,
                        modifier = Modifier.padding(vertical = 12.dp)
                    )
                }

                Spacer(Modifier.height(20.dp))
            }

            // Bottom navigation
            NavigationBar(
                containerColor = Color.White,
                tonalElevation = 8.dp
            ) {
                listOf(
                    "Home" to "⌂",
                    "Explore" to "⌕",
                    "Profile" to "☺"
                ).forEach { item ->
                    NavigationBarItem(
                        selected = selectedTab == item.first,
                        onClick = { selectedTab = item.first },
                        icon = {
                            Text(item.second, fontSize = 22.sp)
                        },
                        label = {
                            Text(item.first, fontSize = 11.sp)
                        },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = Forest,
                            selectedTextColor = Forest,
                            indicatorColor = Mint,
                            unselectedIconColor = Muted,
                            unselectedTextColor = Muted
                        )
                    )
                }
            }
        }
    }
}

@Composable
fun CategoryChip(
    name: String,
    emoji: String,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    Column(
        modifier = modifier
            .background(
                if (selected) Mint else Color.White,
                RoundedCornerShape(16.dp)
            )
            .clickable { onClick() }
            .padding(vertical = 14.dp, horizontal = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(emoji, fontSize = 22.sp)
        Spacer(Modifier.height(7.dp))
        Text(
            name,
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold,
            color = Forest
        )
    }
}

@Composable
fun ProductCard(
    emoji: String,
    name: String,
    price: String,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .background(Color.White, RoundedCornerShape(18.dp))
            .padding(12.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(105.dp)
                .background(Cream, RoundedCornerShape(14.dp)),
            contentAlignment = Alignment.Center
        ) {
            Text(emoji, fontSize = 46.sp)
        }

        Spacer(Modifier.height(11.dp))

        Text(
            name,
            color = Forest,
            fontWeight = FontWeight.SemiBold,
            fontSize = 13.sp,
            lineHeight = 18.sp,
            minLines = 2
        )

        Spacer(Modifier.height(5.dp))

        Text(
            price,
            color = Forest,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 16.sp
        )

        Spacer(Modifier.height(10.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Mint, RoundedCornerShape(10.dp))
                .clickable { }
                .padding(vertical = 9.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "View item  →",
                color = Forest,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
fun TagbandhuDashboard(
    token: String,
    loggedInName: String
) {
    val context = LocalContext.current
    var scannedResult by remember { mutableStateOf<String?>(null) }
    var showProfile by remember { mutableStateOf(false) }
    var userName by remember { mutableStateOf("") }
    var userPhone by remember { mutableStateOf("") }
    var userEmail by remember { mutableStateOf("") }
    var profileLoading by remember { mutableStateOf(false) }
    var profileSaving by remember { mutableStateOf(false) }
    var profileMessage by remember { mutableStateOf("") }

    var realTags by remember {
        mutableStateOf<List<TagItem>>(emptyList())
    }

    var tagsLoading by remember { mutableStateOf(true) }
    var tagsMessage by remember { mutableStateOf("") }

    LaunchedEffect(token) {
        ApiClient.service.getMyTags("Bearer $token")
            .enqueue(object : Callback<TagsResponse> {

                override fun onResponse(
                    call: Call<TagsResponse>,
                    response: Response<TagsResponse>
                ) {
                    tagsLoading = false

                    if (response.isSuccessful &&
                        response.body()?.success == true
                    ) {
                        realTags = response.body()!!.tags
                        tagsMessage = ""
                    } else {
                        tagsMessage =
                            "Tags load nahi hue. Dobara login karo."
                    }
                }

                override fun onFailure(
                    call: Call<TagsResponse>,
                    t: Throwable
                ) {
                    tagsLoading = false
                    tagsMessage = "Server se tags load nahi hue."
                }
            })
    }

    LaunchedEffect(token) {
        profileLoading = true
        ApiClient.service.getProfile("Bearer $token")
            .enqueue(object : Callback<ProfileResponse> {

                override fun onResponse(
                    call: Call<ProfileResponse>,
                    response: Response<ProfileResponse>
                ) {
                    profileLoading = false
                    val result = response.body()

                    if (response.isSuccessful &&
                        result?.success == true &&
                        result.user != null
                    ) {
                        userName = result.user.name
                        userEmail = result.user.email
                        userPhone = result.user.phone
                        profileMessage = ""
                    } else {
                        profileMessage =
                            result?.message ?: "Profile load nahi hui."
                    }
                }

                override fun onFailure(
                    call: Call<ProfileResponse>,
                    t: Throwable
                ) {
                    profileLoading = false
                    profileMessage =
                        "Profile load nahi hui. Server check karo."
                }
            })
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Cream)
            .verticalScroll(rememberScrollState())
            .padding(20.dp)
    ) {
        Text(
            "Tagbandhu",
            fontSize = 28.sp,
            fontWeight = FontWeight.ExtraBold,
            color = Forest
        )

        Text(
            "Your items, always connected.",
            color = Muted,
            fontSize = 14.sp
        )

        Spacer(Modifier.height(24.dp))

        Text(
            "My Dashboard",
            fontSize = 23.sp,
            fontWeight = FontWeight.Bold,
            color = Forest
        )

        Spacer(Modifier.height(16.dp))

        DashboardCard(
            "🏷️",
            "My Tags",
            "View your registered tags",
            onClick = {
                Toast.makeText(
                    context,
                    "Your tags are listed below",
                    Toast.LENGTH_SHORT
                ).show()
            }
        )

        DashboardCard(
            "📷",
            "Scan QR",
            "Scan a tag to identify an item",
            onClick = {
                val activity = context as? Activity

                if (activity != null) {
                    GmsBarcodeScanning.getClient(activity)
                        .startScan()
                        .addOnSuccessListener { barcode ->
                            scannedResult =
                                barcode.rawValue ?: "QR code empty hai"

                            Toast.makeText(
                                context,
                                "QR scan successful!",
                                Toast.LENGTH_SHORT
                            ).show()
                        }
                        .addOnCanceledListener {
                            Toast.makeText(
                                context,
                                "Scan cancelled",
                                Toast.LENGTH_SHORT
                            ).show()
                        }
                        .addOnFailureListener {
                            Toast.makeText(
                                context,
                                "Scanner start nahi hua",
                                Toast.LENGTH_SHORT
                            ).show()
                        }
                }
            }
        )


        DashboardCard(
            "👤",
            "My Profile",
            "Manage your account",
            onClick = {
                showProfile = !showProfile
            }
        )

        if (showProfile) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color.White, RoundedCornerShape(18.dp))
                    .padding(16.dp)
            ) {
                Text(
                    "My Profile",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = Forest
                )

                Spacer(Modifier.height(12.dp))

                if (profileLoading) {
                    CircularProgressIndicator()
                    Spacer(Modifier.height(8.dp))
                }

                OutlinedTextField(
                    value = userName,
                    onValueChange = { userName = it },
                    label = { Text("Your name") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    enabled = !profileSaving
                )

                Spacer(Modifier.height(8.dp))

                OutlinedTextField(
                    value = userEmail,
                    onValueChange = {},
                    label = { Text("Email address") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    enabled = false
                )

                Spacer(Modifier.height(8.dp))

                OutlinedTextField(
                    value = userPhone,
                    onValueChange = { userPhone = it },
                    label = { Text("Phone number") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    enabled = !profileSaving
                )

                Spacer(Modifier.height(12.dp))

                Button(
                    onClick = {
                        if (userName.isBlank()) {
                            profileMessage = "Name required hai."
                            return@Button
                        }

                        profileSaving = true
                        profileMessage = ""

                        ApiClient.service.updateProfile(
                            "Bearer $token",
                            ProfileUpdateRequest(
                                name = userName.trim(),
                                phone = userPhone.trim()
                            )
                        ).enqueue(object : Callback<ProfileResponse> {

                            override fun onResponse(
                                call: Call<ProfileResponse>,
                                response: Response<ProfileResponse>
                            ) {
                                profileSaving = false
                                val result = response.body()

                                if (response.isSuccessful &&
                                    result?.success == true &&
                                    result.user != null
                                ) {
                                    userName = result.user.name
                                    userEmail = result.user.email
                                    userPhone = result.user.phone
                                    profileMessage =
                                        "Profile successfully updated."
                                } else {
                                    profileMessage =
                                        result?.message
                                            ?: "Profile update nahi hui."
                                }
                            }

                            override fun onFailure(
                                call: Call<ProfileResponse>,
                                t: Throwable
                            ) {
                                profileSaving = false
                                profileMessage =
                                    "Server connection failed. Dobara try karo."
                            }
                        })
                    },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !profileLoading && !profileSaving
                ) {
                    Text(
                        if (profileSaving) "Saving..."
                        else "Save Changes"
                    )
                }

                if (profileMessage.isNotBlank()) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = profileMessage,
                        color = if (
                            profileMessage.contains(
                                "successfully",
                                ignoreCase = true
                            )
                        ) Forest
                        else MaterialTheme.colorScheme.error
                    )
                }
            }
        }
        Text(
            "My Registered Tags",
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            color = Forest
        )

        Spacer(Modifier.height(10.dp))

        if (tagsLoading) {
            CircularProgressIndicator()
        } else if (tagsMessage.isNotBlank()) {
            Text(
                tagsMessage,
                color = MaterialTheme.colorScheme.error
            )
        } else if (realTags.isEmpty()) {
            Text(
                "Abhi tumhare account mein koi tag nahi hai.",
                color = Muted
            )
        } else {
            realTags.forEach { tag ->
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 10.dp)
                        .background(Color.White, RoundedCornerShape(16.dp))
                        .padding(16.dp)
                ) {
                    Text(
                        tag.tag_type.replaceFirstChar { it.uppercase() },
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                        color = Forest
                    )

                    Spacer(Modifier.height(5.dp))

                    Text("Tag ID: ${tag.id}", color = Muted)
                    Text("Code: ${tag.tag_code}", color = Muted)

                    Text(
                        if (tag.is_active) "Status: Active"
                        else "Status: Inactive",
                        color = Forest
                    )
                }
            }
        }

        scannedResult?.let { result ->
            Spacer(Modifier.height(12.dp))

            Text(
                "Last Scanned QR",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = Forest
            )

            Spacer(Modifier.height(8.dp))

            Text(
                result,
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color.White, RoundedCornerShape(16.dp))
                    .padding(16.dp),
                fontSize = 15.sp,
                color = Forest
            )
        }
    }
}

@Composable
fun DashboardCard(
    emoji: String,
    title: String,
    description: String,
    onClick: () -> Unit = {}
) {
    val cardLabel = when (title) {
        "My Tags" -> "TAG"
        "Scan QR" -> "QR"
        "My Profile" -> "USER"
        else -> "TB"
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 12.dp)
            .background(
                Color.White,
                RoundedCornerShape(20.dp)
            )
            .clickable { onClick() }
            .padding(18.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(54.dp)
                .background(
                    Mint,
                    RoundedCornerShape(16.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = cardLabel,
                color = Forest,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(Modifier.width(16.dp))

        Column(
            modifier = Modifier.weight(1f)
        ) {
            Text(
                text = title,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = Forest
            )

            Spacer(Modifier.height(5.dp))

            Text(
                text = description,
                fontSize = 13.sp,
                color = Muted,
                lineHeight = 19.sp
            )
        }

        Text(
            text = "›",
            fontSize = 28.sp,
            color = Forest
        )
    }
}